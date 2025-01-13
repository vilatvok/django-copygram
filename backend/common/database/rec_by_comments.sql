CREATE OR REPLACE FUNCTION get_rec_by_comms(users integer[])
RETURNS TABLE(
    user_id integer,
    owner_id bigint,
    post_id bigint,
    is_commented integer
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
            WHEN r1.owner_id IS NOT NULL THEN 1
            ELSE 0
        END
    FROM (
        SELECT unnest(users) AS from_user_id
    ) u1 
    CROSS JOIN (
        SELECT blogs_post.owner_id, blogs_comment.post_id
        FROM blogs_post
        JOIN blogs_comment ON blogs_post.id = blogs_comment.post_id       
        WHERE blogs_comment.owner_id = ANY(users[2:])
    ) p1
    LEFT JOIN blogs_comment r1
    ON u1.from_user_id = r1.owner_id 
        AND p1.post_id = r1.post_id
    ORDER BY 1, 2;
END;
$$;
