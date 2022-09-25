import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Comment, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Текст поста',
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_create(self):
        """Валидная запись создает запись в пост"""
        posts_count = Post.objects.count()
        text = 'Текстовый текст'
        uploaded = SimpleUploadedFile(
            name='some_gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': text,
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user.username}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        tested_post = Post.objects.order_by('id').last()
        self.assertEqual(tested_post.author, self.user)
        self.assertEqual(tested_post.group, self.group)
        self.assertEqual(tested_post.text, text)
        self.assertTrue(tested_post.image)

    def test_post_edit(self):
        """"Валидная форма редактирует запись в Post"""
        posts_count = Post.objects.count()
        text = 'Текстовый текст'
        uploaded = SimpleUploadedFile(
            name='some_gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': text,
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(Post.objects.count(), posts_count)
        post_query = Post.objects.filter(
            id=self.post.id,
            author=self.user,
            group=None,
            text=text
        )
        self.assertTrue(post_query.exists())
        self.assertTrue(post_query.get().image)

    def test_create_comment(self):
        """Проверка работы комментирования."""
        comments_count = Comment.objects.count()
        text = 'Текстовый текст'
        form_data = {
            'text': text,
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        tested_comment = Comment.objects.order_by('id').last()
        self.assertEqual(tested_comment.author, self.user)
        self.assertEqual(tested_comment.post, self.post)
        self.assertEqual(tested_comment.text, text)

    def test_title_label(self):
        text_label = PostFormTests.form.fields['text'].label
        group_label = PostFormTests.form.fields['group'].label
        self.assertEqual(text_label, 'Текст')
        self.assertEqual(group_label, 'Группа')

    def test_title_help_text(self):
        title_help_text = PostFormTests.form.fields['text'].help_text
        group_help_text = PostFormTests.form.fields['group'].help_text
        self.assertEqual(title_help_text, 'Введите текст поста')
        self.assertEqual
        (group_help_text, 'Выберите группу в которой будет опубликован пост')