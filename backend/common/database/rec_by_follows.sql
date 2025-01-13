CREATE OR REPLACE FUNCTION get_rec_by_follows(
    user_id integer,
    users_follow integer[]
)
RETURNS TABLE(
    from_user_id bigint,
    to_user_id bigint,
    is_following integer,
    post_id bigint
)
LANGUAGE plpgsql 
AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT 
        u1.from_user_id, 
        u2.to_user_id, 
        CASE 
            WHEN uf.to_user_id IS NOT NULL THEN 1
            ELSE 0
        END AS is_following,
        p.id AS post_id
    FROM (
        SELECT user_id AS from_user_id
        
        UNION ALL
        
        SELECT q1.to_user_id AS from_user_id
        FROM users_follower q1 
        WHERE q1.from_user_id = user_id
    ) u1
    CROSS JOIN (
        SELECT q2.to_user_id 
        FROM users_follower q2 
        WHERE q2.from_user_id = ANY(users_follow) 
            AND user_id NOT IN (q2.from_user_id, q2.to_user_id)
    ) u2
    LEFT JOIN users_follower uf 
    ON u1.from_user_id = uf.from_user_id AND 
        u2.to_user_id = uf.to_user_id
    LEFT JOIN LATERAL (
        SELECT blogs_post.id
        FROM blogs_post
        WHERE blogs_post.owner_id = u2.to_user_id
        ORDER BY blogs_post.created_at DESC -- Беремо останній пост
        LIMIT 1
    ) p ON true -- Приєднуємо найновіший пост
    ORDER BY 1, 2;
END;
$$;