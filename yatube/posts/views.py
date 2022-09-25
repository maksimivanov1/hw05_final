from django.shortcuts import render
from django.shortcuts import redirect
from .models import Post, Group, Follow
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .forms import PostForm, CommentForm
from django.contrib.auth.decorators import login_required
from posts import utils


User = get_user_model()


def index(request):
    post_list = Post.objects.all().order_by('-pub_date')
    page_obj = utils.paginating(request, post_list)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = Post.objects.all().order_by('-pub_date')
    page_obj = utils.paginating(request, post_list)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.select_related('group')
    following = request.user.is_authenticated and Follow.objects.filter(
        author=author,
        user=request.user
    ).exists()
    page_obj = utils.paginating(request, post_list)
    context = {
        'author': author,
        'page_obj': page_obj,
        'following': following
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post.objects.select_related(), id=post_id)
    comments = post.comments.all()
    form = CommentForm()
    context = {
        'post': post,
        'form': form,
        'comments': comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    context = {'form': form}
    if request.method == 'POST':
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:profile', request.user.username)
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    context = {'form': form,
               'is_edit': True,
               'post_id': post_id}
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    if request.method == 'POST':
        if form.is_valid():
            post = form.save(commit=False)
            post.save()
            return redirect('posts:post_detail', post_id)
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    page_obj = utils.paginating(request, posts)
    context = {
        'page_obj': page_obj
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(
            author=author,
            user=request.user,
        )
    return redirect('posts:profile', username=username)


# Дизлайк, отписка
@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(
        author=author,
        user=request.user,
    ).delete()
    return redirect('posts:profile', username=username)
