from django.forms import ModelForm
from .models import Comment, Post


class PostForm(ModelForm):
    class Meta():
        model = Post
        fields = ['text', 'group', 'image']
        labels = {'text': 'Текст поста', 'group': 'Группа поста'}
        help_text = {'text': 'Текст нового поста',
                     'group': 'Группа которой будет присвоен пост'}

class CommentForm(ModelForm):
    class Meta():
        model = Comment
        fields = ['text']