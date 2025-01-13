# Description

This project is a clone of the popular social media platform Instagram, where users can create and manage
accounts, upload photos, follow others, and interact with posts. The backend is built with Django and Django
Rest Framework, ensuring flexibility and scalability. It uses PostgreSQL for data storage, Redis for caching to
improve performance, and Celery for background task processing. Real-time features, including a chat
application, live feed updates, and notifications, are powered by JavaScript and Django Channels. The project is
containerized with Docker for easy deployment and is hosted on an AWS EC2 instance for reliable and scalable
hosting. It also leverages Amazon S3 for secure and efficient storage of uploaded media files. Additionally, a
recommendation system suggests users and posts based on interactions and preferences.

## Key Features

- **Accounts:** Register/login (including social authentication) and manage user accounts.
- **Publications:** Users can publish posts and stories.
- **Posts manipulations:** Users can manage posts (likes, comments, etc.).
- **Chats:** Users can communicate with each other in private chats or group rooms.
- **Followers System:** Users can follow and unfollow each other.
- **Blocking System:** Users can block other users.
- **Recommendation System:** Users can see recommendations based on their followers.
- **Referral System:** Users can invite people and get privileges in return.
- **Notification System:** Users can receive notifications about various actions.
