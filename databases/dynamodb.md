1. Post_Stage

```
    Primary Key = user_id (String)
    Sort Key = post_id (String)
    Secondary Index
        Sort Key = calendar_stage_uuid (String)
```
        
2. user_processed_posts
```
    Primary Key = user_id (String)
    Sort Key = calendar_id (String)
```

3. user_role_group_id
```
    Primary Key = user_id (String)
    Items should have role_group_id (int)
```