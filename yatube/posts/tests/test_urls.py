from http import HTTPStatus
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from posts.models import Group, Post

User = get_user_model()


class PostsAllURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='max888')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.user_author = User.objects.create_user(username='Author')
        cls.author = Client()
        cls.author.force_login(cls.user_author)

        cls.post = Post.objects.create(
            author=cls.user_author,
            text='Тестовая запись для создания нового поста',
            id=5)

        cls.group = Group.objects.create(
            title=('Заголовок для тестовой группы'),
            slug='test_slug'
        )

    def test_pages(self):
        """URL-страниц доступные всем."""
        url_names = (
            '/',
            reverse('posts:groups', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),

        )
        for adress in url_names:
            with self.subTest():
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_for_authorized(self):
        """Страница /create доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': reverse('posts:groups',
                                             kwargs={'slug': self.group.slug}),
            'posts/create_post.html': reverse('posts:post_create'),
            'posts/profile.html':
            reverse('posts:profile', kwargs={'username': self.user.username}),
            'posts/follow.html': reverse('posts:follow_index')
        }
        for template, url in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_unexisting_page_404(self):
        """Несуществующая страница не найдена."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_detail_pages_authorized_uses_correct_template(self):
        """URL-адреса используют шаблон posts/post_detail.html."""
        response = self.authorized_client.\
            get(reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertTemplateUsed(response, 'posts/post_detail.html')

    def test_post_edit(self):
        """Страница /post_edit от автора поста возвращает статус 200."""
        response = self.author.\
            get(reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_detail_is_auth(self):
        """Страница /post_detail доступна авторизированому юзеру"""
        response = self.authorized_client.\
            get(reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_detail_no_auth(self):
        """Страница /post_detail доступна неавторизированому юзеру"""
        response = self.guest_client.\
            get(reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_private_url(self):
        """
        Без авторизации приватные URL недоступны
        и редиректы работают верно.
        """
        response_unfollow = self.authorized_client.\
            get(reverse('posts:profile_unfollow', kwargs={
                'username': self.user.username}))
        response_follow = self.authorized_client.\
            get(reverse('posts:profile_follow', kwargs={
                'username': self.user.username}))
        url_names = (
            '/admin/',
            '/create',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
            reverse(
                'posts:add_comment', kwargs={'post_id': self.post.id}),
            reverse('posts:follow_index')
        )
        for adress in url_names:
            with self.subTest():
                response = self.guest_client.get(adress)
                self.assertIsNot(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response_follow, reverse(
            'posts:profile', kwargs={'username': self.user.username}))
        self.assertRedirects(response_unfollow, reverse('posts:index'))

    def test_post_edit_no_auth_redirect(self):
        """Страница /post_edit для анонима производит редирект."""
        response = self.guest_client.\
            get(reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        self.assertRedirects(response, ('/auth/login/?next=/posts/5/edit/'))

    def test_post_edit_no_auth_redirect(self):
        """Страница /post_edit для auth_клиента производит редирект."""
        response = self.authorized_client.\
            get(reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))

    def test_post_edit_page_author_uses_correct_template(self):
        """URL-адрес использует шаблон create_post.html для автора."""
        response = self.author.\
            get(reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        self.assertTemplateUsed(response, 'posts/create_post.html')
