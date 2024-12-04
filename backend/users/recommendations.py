import pandas as pd

from sklearn.metrics.pairwise import cosine_similarity
from django.db import connection
from django.db.models import Q
from celery.result import allow_join_result

from common import redis_client
from blogs.models import Post
from blogs.tasks import update_posts_recommendations
from users.models import User


class RedisCoordinator:
    def __init__(self, key: str):
        self.key = key

    def store_recommendations(self, recommendations) -> None:
        if recommendations:
            redis_client.sadd(self.key, *recommendations)

    def clear_recommendations(self) -> None:
        redis_client.delete(self.key)

    def remove_recommendations(self, recommendations) -> None:
        if recommendations:
            redis_client.srem(self.key, *recommendations)

    def get_recommendations(self) -> set[int]:
        resp = redis_client.smembers(self.key)
        return set(map(int, resp))


class BaseRecommendation:
    query = None
    matrix_type = None

    def __init__(self, user: User) -> None:
        self.user = user
        self.df = None
        self.matrix = None
        self.similarities = None

    def get_db_data(self, **kwargs) -> tuple:
        query = self.get_query()
        params = self.get_query_params(**kwargs)
        if not params:
            return

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            data = cursor.fetchall()

        if not data:
            return
        return {'columns': columns, 'data': data}

    def get_query(self) -> str:
        return self.query

    @staticmethod
    def get_query_params(**kwargs) -> dict:
        similar_users = sorted(kwargs['similar_users'])
        params = {'users': similar_users}
        return params

    def generate_recommendations(self, db_response, for_: str) -> set:
        if not db_response:
            return set()
        return self.generate_data(db_response, for_)

    def create_matrix(self, db_response) -> tuple:
        df = pd.DataFrame(db_response['data'], columns=db_response['columns'])
        df = df.dropna(subset=['post_id'])

        match self.matrix_type:
            case 'follows':
                matrix = df.pivot(
                    index='from_user_id',
                    columns='to_user_id',
                    values='is_following',
                )
            case 'likes':
                matrix = df.pivot(
                    index='user_id',
                    columns='post_id',
                    values='is_liked',
                )
            case 'comments':
                matrix = df.pivot(
                    index='user_id',
                    columns='post_id',
                    values='is_commented',
                )
            case 'saved':
                matrix = df.pivot(
                    index='user_id',
                    columns='post_id',
                    values='is_saved',
                )
        return df, matrix

    @staticmethod
    def generate_cosine_similarity(v1, v2):
        v1 = v1.values.reshape(1, -1)
        v2 = v2.values.reshape(1, -1)
        return cosine_similarity(v1, v2)[0][0]

    def compute_similarities(self) -> pd.DataFrame:
        user_id = self.user.id
        user_row = self.matrix.loc[user_id, :]
        similarities = self.matrix.apply(
            lambda row: self.generate_cosine_similarity(user_row, row),
            axis=1,
        )
        similarities = similarities.to_frame(name='similarity').sort_values(
            by='similarity',
            ascending=False,
        )
        return similarities.drop(user_id).head(3)

    def generate_data(self, db_response, for_: str) -> set:
        df, matrix = self.create_matrix(db_response)

        self.df = df
        self.matrix = matrix

        similarities = self.compute_similarities()
        self.similarities = similarities.index.to_list()
        # Add current user to the list of similar users
        user_id = self.user.id
        self.similarities.append(user_id)

        untracked_items = matrix.loc[user_id, matrix.loc[user_id] == 0].index

        if untracked_items.empty:
            return set()

        if for_ == 'posts':
            return self.find_new_posts(similarities, untracked_items)
        if for_ == 'follows':
            return self.find_new_users(similarities, untracked_items)

    def find_new_users(
        self,
        similarities: pd.DataFrame,
        untracked_posts: pd.Index,
    ) -> set:
        new_users = set()
        df = self.df
        for post in untracked_posts:
            for s in similarities.index:
                if self.matrix.loc[s, post]:
                    owner_id = df.loc[df['post_id'] == post, 'owner_id']
                    new_users.add(int(owner_id.values[0]))
                    break
        return new_users

    def find_new_posts(
        self,
        similarities: pd.DataFrame,
        untracked_posts: pd.Index,
    ) -> set:
        new_posts = set()
        for post in untracked_posts:
            for s in similarities.index:
                if self.matrix.loc[s, post]:
                    new_posts.add(int(post))
                    break
        return new_posts


class RecommendationsByFollows(BaseRecommendation):
    query = 'SELECT * FROM get_rec_by_follows(%(user_id)s, %(following)s)'
    matrix_type = 'follows'

    @staticmethod
    def get_query_params(**kwargs) -> dict:
        user = kwargs['user']
        users = list(user.following.values_list('to_user_id', flat=True))
        if not users:
            return set()
        params = {'user_id': user.id, 'following': users}
        return params

    def find_new_users(
        self,
        similarities: pd.DataFrame,
        untracked_users: pd.Index,
    ) -> set:
        new_users = set()
        for user in untracked_users:
            for s in similarities.index:
                if self.matrix.loc[s, user]:
                    new_users.add(int(user))
                    break
        return new_users

    def find_new_posts(
        self,
        similarities: pd.DataFrame,
        untracked_users: pd.Index,
    ) -> set:
        new_posts = set()
        df = self.df
        for user in untracked_users:
            for s in similarities.index:
                if self.matrix.loc[s, user]:
                    post_id = df.loc[df['to_user_id'] == user, 'post_id']
                    if not post_id.empty:
                        new_posts.add(int(post_id.values[0]))
                    break
        return new_posts


class RecommendationsByLikes(BaseRecommendation):
    query = 'SELECT * FROM get_rec_by_likes(%(users)s)'
    matrix_type = 'likes'


class RecommendationsByComments(BaseRecommendation):
    query = 'SELECT * FROM get_rec_by_comms(%(users)s)'
    matrix_type = 'comments'


class RecommendationsBySaved(BaseRecommendation):
    query = 'SELECT * FROM get_rec_by_saved(%(users)s)'
    matrix_type = 'saved'


# Main Recommender class that orchestrates recommendations
class Recommender:
    def __init__(self, user: User) -> None:
        self.user = user
        self.redis_follows_coordinator = RedisCoordinator(
            key=f'user:{user.username}:follows_recommendations',
        )
        self.redis_posts_coordinator = RedisCoordinator(
            key=f'user:{user.username}:posts_recommendations',
        )
        self.recs_by_follows = set()
        self.similar_users = set()

    def load_db_data(self):
        """Load data from the database and store it in the class instance."""
        
        follows = RecommendationsByFollows(self.user)
        self.follows_data = follows.get_db_data(user=self.user)
        self.set_similar_users(instance=follows)
        
        rec_classes = [
            RecommendationsByLikes,
            RecommendationsByComments,
            RecommendationsBySaved,
        ]
        for rec_class in rec_classes:
            rec_instance: BaseRecommendation = rec_class(self.user)
            similar_users = self.similar_users.copy()
            data = rec_instance.get_db_data(similar_users=similar_users)
            class_name = rec_class.__name__.lower()[len('recommendationsby'):]
            self.__setattr__(f'{class_name}_data', data)

    def set_similar_users(self, instance) -> set:
        """Get similar users based on the follows data."""
        if self.follows_data:
            self.recs_by_follows = instance.generate_recommendations(
                db_response=self.follows_data,
                for_='follows',
            )
            self.similar_users = instance.similarities

    def _generate_recommendations_(self, for_: str) -> set:
        rec_classes = [
            RecommendationsByFollows,
            RecommendationsByLikes,
            RecommendationsByComments,
            RecommendationsBySaved,
        ]

        recommendations = set()
        for rec_class in rec_classes:
            rec_instance: BaseRecommendation = rec_class(self.user)
            class_name = rec_class.__name__.lower()[len('recommendationsby'):]
            db_response = getattr(self, f'{class_name}_data')
            recs = rec_instance.generate_recommendations(
                db_response=db_response,
                for_=for_,
            )
            recommendations |= recs
        return recommendations

    def generate_follow_recommendations(self) -> set:
        redis_coordinator = self.redis_follows_coordinator
        recs_by_follows = self.recs_by_follows
        if not len(recs_by_follows):
            recs = self.complete_recommendations(redis_coordinator)
        else:
            recs = self._generate_recommendations_(for_='follows')
            recs |= self.complete_recommendations(redis_coordinator)
        redis_coordinator.store_recommendations(recs)
        return recs

    def generate_post_recommendations(self) -> set:
        redis_coordinator = self.redis_posts_coordinator
        recs = self._generate_recommendations_(for_='posts')

        # Exclude uninteresting posts
        uninteresting_posts = self.user.uninteresting_posts.values_list(
            'post_id',
            flat=True,
        )
        uninteresting_posts = list(
            Post.objects.annotated().
            filter(id__in=uninteresting_posts).
            values('description', 'file')
        )
        posts = list(
            Post.objects.annotated().
            filter(id__in=recs).
            values('id', 'description', 'file')
        )

        if len(uninteresting_posts) and len(posts):
            # ? Probably should be moved to a separate method
            exclude = update_posts_recommendations.delay(
                uninteresting_posts,
                posts,
            )
            with allow_join_result():
                exclude = exclude.get()
            recs = recs.difference(exclude)

        recs |= self.complete_recommendations(redis_coordinator)
        redis_coordinator.store_recommendations(recs)
        return recs

    def generate_recommendations(self) -> None:
        self.load_db_data()
  
        # Clear all recommendations
        self.redis_follows_coordinator.clear_recommendations()
        self.redis_posts_coordinator.clear_recommendations()

        response = self.generate_follow_recommendations()
        if len(response):
            self.generate_post_recommendations()

    def complete_recommendations(self, coordinator, amount: int = 50) -> None:
        recommendations = coordinator.get_recommendations()
        size = len(recommendations)
        if size < amount:
            curr_user = self.user
            count = amount - size
            if coordinator == self.redis_follows_coordinator:
                recs_with_user = recommendations.copy()
                recs_with_user.add(curr_user.id)
                additional = (
                    User.objects.
                    exclude(
                        Q(id__in=recs_with_user) |
                        Q(followers__from_user=curr_user)
                    ).
                    order_by('?').
                    values_list('id', flat=True)
                )
            elif coordinator == self.redis_posts_coordinator:
                # Get random posts
                following = curr_user.following.values_list(
                    'to_user_id',
                    flat=True,
                )
                curr_user_posts = curr_user.posts.values_list('id', flat=True)
                additional = list(
                    Post.objects.
                    annotated().
                    exclude(
                        Q(id__in=curr_user_posts) |
                        Q(owner_id__in=following)
                    ).
                    order_by('?').
                    values('id', 'description', 'file')
                )

                # Get viewed posts
                viewed_posts_key = f'user:{curr_user.username}:viewed_posts'
                viewed_posts = redis_client.smembers(viewed_posts_key)
                viewed_posts_qs = list(
                    Post.objects.annotated().
                    filter(id__in=set(map(int, viewed_posts))).
                    values('description', 'file')
                )
                # Receive similar posts to the viewed ones
                if len(additional) and len(viewed_posts_qs):
                    filter_additional_posts = update_posts_recommendations.delay(
                        viewed_posts_qs,
                        additional
                    )
                    with allow_join_result():
                        additional = list(filter_additional_posts.get())
                else:
                    additional = set()

            if len(additional):
                additional_recommendations = set(additional[:count])
                return additional_recommendations
        return set()

    def get_follows_ids(self) -> set[int]:
        return self.redis_follows_coordinator.get_recommendations()

    def get_posts_ids(self) -> set[int]:
        return self.redis_posts_coordinator.get_recommendations()
