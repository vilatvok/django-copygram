CREATE OR REPLACE FUNCTION get_rec_by_likes(users integer[])
RETURNS TABLE(
    user_id integer,
    owner_id bigint,
    post_id bigint,
    is_liked integer
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        u1.from_user_id,
        p1.owner_id,
        p1.post_id,
        CASE
            WHEN r1.user_id IS NOT NULL THEN 1
            ELSE 0
        END
    FROM (
        SELECT unnest(users) AS from_user_id
    ) u1 
    CROSS JOIN (
        SELECT blogs_post.owner_id, blogs_post_likes.post_id 
        FROM blogs_post
        JOIN blogs_post_likes ON blogs_post.id = blogs_post_likes.post_id       
        WHERE blogs_post_likes.user_id = ANY(users[2:])
    ) p1
    LEFT JOIN blogs_post_likes r1
    ON u1.from_user_id = r1.user_id 
        AND p1.post_id = r1.post_id
    ORDER BY 1, 2;
END;
$$;
