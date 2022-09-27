from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Group, Post, Follow, Comment
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.conf import settings
import tempfile
import shutil


User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post = Post.objects.create(
            author=User.objects.create_user(username='max1',
                                            email='test1@mail.ru',
                                            password='test_pass',),
            text='Тестовая запись для создания 1 поста',
            group=Group.objects.create(
                title='Заголовок для 1 тестовой группы',
                slug='test-slug1'))

        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small_gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user_author = User.objects.create_user(username='Author')
        cls.author = Client()
        cls.author.force_login(cls.user_author)
        cls.another_author = User.objects.create_user(username='Другой-автор')
        cls.author2 = Client()
        cls.author2.force_login(cls.another_author)

        cls.post2 = Post.objects.create(
            author=User.objects.create_user(username='max2',
                                            email='test2@mail.ru',
                                            password='test_pass',),
            text='Тестовая запись для создания 2 поста',
            id=3,
            image=cls.uploaded,
            group=Group.objects.create(
                title='Заголовок для 2 тестовой группы',
                slug='test-slug2'))

        cls.group_post = Post.objects.create(
            text='Пост другого автора',
            author=cls.another_author,
            image=cls.uploaded,
            group=Group.objects.create(title='Тестовая группа',
                                       slug='test-slug',
                                       description='Тестовое описание'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='max888')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def context_check(self, post):
        """Функция проверки атрибутов контекста."""
        self.assertEqual(self.post2.author, self.post2.author)
        self.assertEqual(self.post2.text, self.post2.text)
        self.assertEqual(self.post2.group, self.post2.group)
        self.assertEqual(self.post2.image, self.post2.image)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': (
                reverse('posts:groups', kwargs={'slug': self.post2.group.slug})
            ),
            'posts/create_post.html': reverse('posts:post_create')
        }
        for template, name in templates_pages_names.items():
            with self.subTest(name=name):
                response = self.authorized_client.get(name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        page_obj = response.context.get('page_obj')
        self.assertIsNotNone(page_obj)
        self.assertGreater(len(page_obj), 0)
        first_object = response.context["page_obj"][0]
        self.assertIsNotNone(first_object)
        self.context_check(first_object)

    def test_group_pages_show_correct_context(self):
        """Шаблон groups сформирован с правильным контекстом."""
        response = self.authorized_client.\
            get(reverse('posts:groups',
                        kwargs={'slug': self.post2.group.slug}))
        first_object_group = response.context["group"]
        first_object_post = response.context["page_obj"][0]
        self.assertIsNotNone(first_object_post)
        self.assertIsNotNone(first_object_group)
        self.assertEqual(first_object_group.title, self.post2.group.title)
        self.assertEqual(first_object_group.slug, self.post2.group.slug)
        self.context_check(first_object_post)

    def test_post_in_another_group(self):
        """Пост не попал в другую группу."""
        response = self.authorized_client.get(
            reverse('posts:groups', kwargs={'slug': self.post.group.slug}))
        first_object = response.context["page_obj"][0]
        self.assertIsNotNone(first_object)
        self.assertIsNot(first_object.text, self.post2.text)

    def test_profile_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username':
                                             self.post2.author.username}))
        page_obj = response.context.get('page_obj')
        self.assertIsNotNone(page_obj)
        self.assertGreater(len(page_obj), 0)
        first_object = response.context["page_obj"][0]
        self.assertIsNotNone(first_object)
        self.context_check(first_object)

    def test_create_page_show_correct_context(self):
        """Шаблон create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_edit_page_show_correct_context(self):
        """Шаблон edit сформирован с правильным контекстом."""
        response = self.author.\
            get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse('posts:post_detail', kwargs={
                'post_id': self.post2.id})))
        first_object = response.context['post']
        self.context_check(first_object)

    def test_cache_index_page(self):
        """Проверяем работу кэша"""
        url = reverse('posts:index')
        responce = self.client.get(url)
        Post.objects.last().delete()
        cached_responce = self.client.get(url)
        cache.clear()
        not_cached_responce = self.client.get(url)
        self.assertEqual(cached_responce.content, responce.content)
        self.assertNotEqual(not_cached_responce.content, responce.content)

    def test_post_for_follower(self):
        """
        Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех,
        кто не подписан.
        """
        author = User.objects.create(username='Автор')
        user_follower = Follow.objects.create(
            user=User.objects.create(username='подписчик'),
            author=author
        )
        self.authorized_client.force_login(user_follower.user)
        user_not_follower = User.objects.create(username='не_подписчик')
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(user_not_follower)
        post_for_following = Post.objects.create(
            author=author,
            text='Текст с большим количеством букв',
            group=Group.objects.create(
                title='Заголовок для 1 тестовой группы',
                slug='test-slug5')
        )
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.author})
        )
        follower_index_url = reverse('posts:follow_index')
        response = self.authorized_client.get(follower_index_url)
        objects = response.context['page_obj']
        self.assertIn(post_for_following, objects)
        # Пост не появляется в ленте у не_подписчика
        response = self.authorized_client2.get(follower_index_url)
        objects_count = len(response.context['page_obj'])
        self.assertEqual(objects_count, 0)

    def test_follow(self):
        """Тест подписки на автора."""
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.another_author.username}))
        self.assertTrue(
            Follow.objects.filter(
                author=self.another_author,
                user=self.user,
            ).exists())

    def test_cannot_follow_yourself(self):
        """Тест подписки на себя."""
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user.username}))
        self.assertFalse(
            Follow.objects.filter(
                author=self.user,
                user=self.user,
            ).exists())

    def test_unfollow(self):
        """Тест отписки."""
        Follow.objects.create(
            author=self.another_author,
            user=self.user,
        )
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.another_author.username}))
        self.assertFalse(
            Follow.objects.filter(
                author=self.another_author,
                user=self.user,
            ).exists())


class TestComment(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='slug4',
            description='Описание',
        )
        cls.test_user = User.objects.create_user(username='Ляо')
        cls.post = Post.objects.create(
            pub_date='31 июля 1854',
            author=cls.test_user,
            text='Бам',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client_author = Client()
        self.authorized_client.force_login(self.test_user)
        self.author = User.objects.create_user(username='Ляо1')
        self.authorized_client_author.force_login(self.author)

    def test_comment_2(self):
        """Проверка работы комментариев."""
        post = Post.objects.create(
            author=self.test_user,
            text='Тест',
        )
        comments_count = Comment.objects.count()
        text = 'Тестовый комментарий'
        form_data = {
            'text': text,
        }
        response = self.authorized_client_author.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, (
            reverse('posts:post_detail', kwargs={'post_id': post.id})))
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(Comment.objects.filter(
            text='Тестовый комментарий',
            author=self.author).exists())


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='max',
                                              email='test@mail.ru',
                                              password='test_pass',)
        cls.group = Group.objects.create(
            title=('Заголовок для тестовой группы'),
            slug='test-slug2',
            description='Тестовое описание')
        cls.posts = []
        for i in range(13):
            cls.posts.append(Post(
                text=f'Тестовый пост {i}',
                author=cls.author,
                group=cls.group
            )
            )
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='max888')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_contains_ten_posts(self):
        """На первую страницу выводится 10 постов."""
        list_urls = {
            reverse("posts:index"): "index",
            reverse("posts:groups", kwargs={"slug": self.group.slug}): "group",
            reverse("posts:profile",
                    kwargs={"username": self.author.username}): "profile",
        }
        for tested_url in list_urls.keys():
            response = self.client.get(tested_url)
            self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_posts(self):
        """На вторую страницу выводитcя 3 поста."""
        list_urls = {
            reverse("posts:index") + "?page=2": "index",
            reverse("posts:groups",
                    kwargs={"slug": self.group.slug}) + "?page=2":
            "group",
            reverse("posts:profile",
                    kwargs={"username": self.author.username}) + "?page=2":
            "profile",
        }
        for tested_url in list_urls.keys():
            response = self.client.get(tested_url)
            self.assertEqual(len(response.context['page_obj']), 3)
