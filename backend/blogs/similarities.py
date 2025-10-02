import pandas as pd
import numpy as np

from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity


class Recognizer:

    def __init__(self):
        self.model = self.get_model()

    @staticmethod
    def get_model():
        from keras.api.applications.vgg16 import VGG16

        return VGG16(weights='imagenet', include_top=False,
                      pooling='max', input_shape=(225, 350, 3))

    def generate_images_embeddings(self, images: list[str]):
        from keras.api.preprocessing.image import load_img, img_to_array
        from keras.api.applications.vgg16 import preprocess_input

        importedImages = []
        for image in images:
            original = load_img(image, target_size=(225, 350))
            numpy_image = img_to_array(original)
            image_batch = np.expand_dims(numpy_image, axis=0) 
            importedImages.append(image_batch)

        images = np.vstack(importedImages)
        preprocessed = preprocess_input(images)
        imgs_embedding = self.model.predict(preprocessed)
        return imgs_embedding

    def compare_images(self, images: list[str]):
        images_vectors = self.generate_images_embeddings(images)
        similarity_score = cosine_similarity(images_vectors)
        return similarity_score

    def generate_images_matrix_similarity(self):
        path = Path('/home/kvydyk/Documents/projects/copygram/backend/media/posts/')
        images = [str(file_path) for file_path in path.rglob('*.jpg')]
        df_cells = [image.split('/')[-1].split('.')[0] for image in images]
    
        res = self.compare_images(images)
        cos_similarities_df = pd.DataFrame(res, columns=df_cells, index=df_cells)
        cos_similarities_df.to_hdf('media/images_similarities.h5', key='data')

    @staticmethod
    def compare_descriptions(first: str, second: str):
        first_words = first.lower().split()
        second_words = second.lower().split()

        unique_words = list(set(first_words + second_words))

        # Initialize the DataFrame with 0s
        df = pd.DataFrame(0, index=['first', 'second'], columns=unique_words)

        # Set 1s for words present in the first sentence
        for word in first_words:
            df.at['first', word] = 1

        # Set 1s for words present in the second sentence
        for word in second_words:
            df.at['second', word] = 1

        # Compute the cosine similarity
        similarity_score = cosine_similarity(
            df.loc['first'].values.reshape(1, -1),
            df.loc['second'].values.reshape(1, -1)
        )[0][0]

        return similarity_score

    def generate_descriptions_embeddings(descrs: list[str]):
        unique_words = set()
        for description in descrs:
            unique_words |= set(description.lower().split())
        unique_words = list(unique_words)
        
        word_embeddings = []
        for description in descrs:
            df = pd.DataFrame(0, index=[description], columns=unique_words)
            words = description.lower().split()
            for word in words:
                df.at[description, word] = 1
            
            word_embeddings.append(df.loc[description].values)  # Save the vector for this description

        # Stack all the description vectors into one numpy array
        return np.vstack(word_embeddings)


if __name__ == '__main__':
    sim = Recognizer()
    sim.generate_images_matrix_similarity()
    print('Done')
