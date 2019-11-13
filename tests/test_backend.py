import unittest
import sys
sys.path.append('..')
from backend import app, user_role_group_id_table, user_processed_post_table, user_stage_table

class TrialTest(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_calendar(self):
        response = self.app.get('/calendar')
        self.assertTrue('results' in response.json)
        months = response.json['results']
        self.assertTrue(len(months) == 2)
        self.assertTrue(months[0] == {'month': 'nov_2019'})
        self.assertTrue(months[1] == {'month': 'oct_2019'})

    def test_rolegroup(self):
        response = self.app.get('/role_groups')
        self.assertTrue('role_groups' in response.json)
        rolegroups = response.json['role_groups']
        self.assertTrue(len(rolegroups) == 2)


class RoleGroupTest(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_null_rolegroup(self):
        response = self.app.get('/users/1/rolegroupid')
        self.assertIsNone(response.json['role_group_id'])

    def test_wrong_user(self):
        user_id = 'fakeuser'
        response = self.app.get('/users/{user_id}/rolegroupid'.format(user_id=user_id))
        self.assertIsNone(response.json['role_group_id'])

    def test_correct_rolegroup(self):
        user_id = 'correct_rolegroup'
        user_role_group_id_table.put_item(
            Item={
                'user_id': user_id,
                'role_group_id': 1
            })

        response = self.app.get('/users/{user_id}/rolegroupid'.format(user_id=user_id))
        self.assertTrue('role_group_id' in response.json)
        self.assertTrue(response.json['role_group_id'] == 1)
        self.assertTrue('user_id' in response.json)
        self.assertTrue(response.json['user_id'] == user_id)

    def test_update_rolegroup(self):
        user_id = 'update_rolegroup'
        response = self.app.post('/users/{user_id}/rolegroupid'.format(user_id=user_id), data={'role_group_id': 1})
        self.assertTrue('role_group_id' in response.json)
        self.assertTrue(response.json['role_group_id'] == 1)
        self.assertTrue('user_id' in response.json)
        self.assertTrue(response.json['user_id'] == user_id)

        dynamodb_response = user_role_group_id_table.get_item(Key={'user_id': user_id})
        self.assertTrue('Item' in dynamodb_response)
        response = dynamodb_response['Item']
        self.assertTrue('role_group_id' in response)
        self.assertTrue(response['role_group_id'] == 1)
        self.assertTrue('user_id' in response)
        self.assertTrue(response['user_id'] == user_id)


class UpdatePosts(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_update_post(self):
        user_id = 'update_post'
        post_id = 1
        calendar_id = 'never_2019'
        stage_id = 1
        payload = {'calendar_id': calendar_id, 'stage_id': stage_id, 'post_id': post_id}
        response = self.app.post('/users/{user_id}/posts'.format(user_id=user_id), data=payload)
        self.assertTrue('code' in response.json and response.json['code'] == 200)

        dynamodb_response = user_stage_table.get_item(Key={'user_id': user_id, 'post_id': str(post_id)})
        self.assertTrue('Item' in dynamodb_response)
        response = dynamodb_response['Item']
        self.assertTrue('calendar_stage_uuid' in response)
        self.assertTrue(response['calendar_stage_uuid'] == '|'.join([calendar_id, str(stage_id)]))


class SetLatestPost(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_existing_user(self):
        user_id = 'existing_user2'
        calendar_id = 'never_2019'
        post_id = 100
        user_processed_post_table.put_item(Item={
            'user_id': user_id,
            'calendar_id': calendar_id,
            'post_id': post_id
        })

        response = self.app.get('/users/{user_id}/calendar/{calendar_id}/latest_post'
                                .format(user_id=user_id, calendar_id=calendar_id))
        self.assertTrue('last_processed_post' in response.json)
        self.assertTrue(response.json['last_processed_post'] == post_id)

    def test_new_user(self):
        user_id = 'new_user2'
        calendar_id = 'never_2019'
        response = self.app.get('/users/{user_id}/calendar/{calendar_id}/latest_post'
                                .format(user_id=user_id, calendar_id=calendar_id))
        self.assertTrue('last_processed_post' in response.json)
        self.assertTrue(response.json['last_processed_post'] == 0)

        dynamodb_response = user_processed_post_table.get_item(Key={'user_id': user_id, 'calendar_id': calendar_id})
        self.assertTrue('Item' in dynamodb_response)
        response = dynamodb_response['Item']
        self.assertTrue(response['post_id'] == 0)

    def test_update(self):
        user_id = 'update_post2'
        calendar_id = 'never_2019'
        post_id = 100
        payload = {'latest_post': post_id}
        response = self.app.post('/users/{user_id}/calendar/{calendar_id}/latest_post'
                                 .format(user_id=user_id, calendar_id=calendar_id), data=payload)
        self.assertTrue('last_processed_post' in response.json)
        self.assertTrue(response.json['last_processed_post'] == post_id)

        dynamodb_response = user_processed_post_table.get_item(Key={'user_id': user_id, 'calendar_id': calendar_id})
        self.assertTrue('Item' in dynamodb_response)
        response = dynamodb_response['Item']
        self.assertTrue(response['post_id'] == post_id)


class CreatingRecords(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_get_new_posts(self):
        calendar_id = 'nov_2019'
        last_post = 0
        response = self.app.get('/calendar/{calendar_id}/new_posts'
                                .format(calendar_id=calendar_id), query_string={'last_post': last_post})
        new_posts = response.json
        self.assertTrue('new_posts' in new_posts)
        self.assertTrue(len(new_posts['new_posts']) == 6)
        self.assertTrue(new_posts['new_posts'][0] == 6)
        self.assertTrue(new_posts['new_posts'][-1] == 1)

    def test_batch_records_update(self):
        user_id = 'batch_user'
        calendar_id = 'nov_2019'
        stage_id = 99
        posts = [x for x in range(10)]
        payload = {'user_id': user_id, 'calendar_id': calendar_id, 'stage_id': stage_id, 'post_id_batch': posts}
        self.app.post('/users/{user_id}/batch_posts'.format(user_id=user_id), data=payload)

        for post_id in posts:
            dynamodb_response = user_stage_table.get_item(Key={'user_id': user_id, 'post_id': str(post_id)})
            self.assertTrue('Item' in dynamodb_response)
            response = dynamodb_response['Item']
            self.assertTrue('calendar_stage_uuid' in response)
            self.assertTrue(response['calendar_stage_uuid'] == '|'.join([calendar_id, str(stage_id)]))

    def test_post_ids_in_view(self):
        user_id = 'non_empty_user_postidview'
        calendar_id = 'nov_2019'
        stage_id = 99
        response = self.app.get('/users/{user_id}/calendar/{calendar_id}/stage/{stage_id}/post_ids'
                                .format(user_id=user_id, calendar_id=calendar_id, stage_id=stage_id))
        self.assertTrue('results' in response.json)
        self.assertTrue(response.json['results'] == [1, 2, 3, 4])

    def test_view(self):
        user_id = 'non_empty_view_user'
        calendar_id = 'nov_2019'
        stage_id = 99
        response = self.app.get('/users/{user_id}/calendar/{calendar_id}/stage/{stage_id}/view'
                                .format(user_id=user_id, calendar_id=calendar_id, stage_id=stage_id))
        self.assertTrue('results' in response.json)
        view = response.json['results']
        self.assertTrue(len(view) == 4)
        post_order = [x['post_id'] for x in view]
        self.assertTrue(post_order == [2, 1, 4, 6])

    def test_record_creation_new_user(self):
        user_id = 'new_user_records'
        calendar_id = 'nov_2019'
        response = self.app.post('/users/{user_id}/calendar/{calendar_id}/update_posts'
                                 .format(user_id=user_id, calendar_id=calendar_id))
        stage_id = 0
        print(response.json)

        posts = [x for x in range(1, 6)]
        for post_id in posts:
            dynamodb_response = user_stage_table.get_item(Key={'user_id': user_id, 'post_id': str(post_id)})
            self.assertTrue('Item' in dynamodb_response)
            response = dynamodb_response['Item']
            self.assertTrue('calendar_stage_uuid' in response)
            self.assertTrue(response['calendar_stage_uuid'] == '|'.join([calendar_id, str(stage_id)]))

    def test_record_creation_old_user(self):
        user_id = 'old_user_records'
        calendar_id = 'test_2019'
        last_post = 6
        user_processed_post_table.put_item(Item={
            'user_id': user_id,
            'calendar_id': calendar_id,
            'post_id': last_post
        })
        response = self.app.post('/users/{user_id}/calendar/{calendar_id}/update_posts'
                                 .format(user_id=user_id, calendar_id=calendar_id))
        print(response.json)


if __name__ == '__main__':
    unittest.main()
