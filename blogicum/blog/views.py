from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)

from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.db.models import Q
from django.http import Http404

from .models import Post, Category, Comment
from .forms import CommentForm, UserForm, CreateForm
from django.contrib.auth import get_user_model

User = get_user_model()


class BlogListView(ListView):
    model = Post
    ordering = '-pub_date'
    paginate_by = 10
    template_name = 'blog/index.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True
        ).select_related('category', 'location', 'author')

        queryset = queryset.filter(
            Q(
                location__isnull=True
            ) | Q(
                location__is_published=True
            )
        )

        queryset = queryset.annotate(
            comment_count=Count('comments')
        )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_comments'] = sum(
            post.comment_count for post in context['object_list']
        )
        return context


class BlogPostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'

    def get_object(self, queryset=None):
        post = super().get_object(queryset)
        user = self.request.user

        conditions_failed = []

        if not post.is_published:
            conditions_failed.append('пост не опубликован')
        if post.pub_date > timezone.now():
            conditions_failed.append('дата публикации в будущем')
        if not post.category.is_published:
            conditions_failed.append('категория не опубликована')
        if post.location and not post.location.is_published:
            conditions_failed.append('местоположение не опубликовано')

        if conditions_failed and user != post.author and not user.is_superuser:
            raise Http404(f"Доступ запрещен: {', '.join(conditions_failed)}")

        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        user = self.request.user

        context['form'] = CommentForm()

        context['can_comment'] = (
            post.is_published
            and post.pub_date <= timezone.now()
            and user.is_authenticated
            and post.category.is_published
            and (not post.location or post.location.is_published)
        )

        if (
            post.is_published
            or user == post.author
            or user.is_superuser
        ):
            context['comments'] = post.comments.select_related('author')
        else:
            context['comments'] = []

        return context


class CategoryPostsListView(ListView):
    template_name = 'blog/category.html'
    context_object_name = 'page_obj'
    paginate_by = 10

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.category = get_object_or_404(
            Category.objects.filter(is_published=True),
            slug=self.kwargs['category_slug']
        )

    def get_queryset(self):
        queryset = Post.objects.select_related(
            'category',
            'author',
            'location').filter(
            category=self.category,
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True
        )

        from django.db.models import Q
        queryset = queryset.filter(
            Q(location__isnull=True)
            | Q(location__is_published=True)
        )

        queryset = queryset.annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = CreateForm
    template_name = 'blog/create.html'
    login_url = '/auth/login/'
    redirect_field_name = 'next'

    def form_valid(self, form):
        form.instance.author = self.request.user

        category = form.cleaned_data.get('category')
        location = form.cleaned_data.get('location')

        if category and not category.is_published:
            form.add_error('category', 'Выбранная категория не опубликована')
            return self.form_invalid(form)

        if location and not location.is_published:
            form.add_error(
                'location',
                'Выбранное местоположение не опубликовано')
            return self.form_invalid(form)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username})


@login_required
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)

    if not (post.is_published
            and post.pub_date <= timezone.now()
            and post.category.is_published
            and (not post.location or post.location.is_published)):
        return redirect('blog:post_detail', pk=pk)

    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()

    return redirect('blog:post_detail', pk=pk)


class UserProfileView(DetailView):
    model = User
    template_name = 'blog/profile.html'
    context_object_name = 'profile'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.object
        is_owner = self.request.user == profile

        if is_owner:
            posts = Post.objects.filter(author=profile)
        else:
            posts = Post.objects.filter(
                author=profile,
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True
            )
            from django.db.models import Q
            posts = posts.filter(
                Q(location__isnull=True)
                | Q(location__is_published=True)
            )

        posts = posts.select_related('category', 'location').annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')

        paginator = Paginator(posts, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context.update({
            'page_obj': page_obj,
            'is_owner': is_owner,
        })

        return context


@login_required
def edit_profile(request):
    template = 'blog/user.html'
    if request.method == 'POST':
        form = UserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('blog:profile', username=request.user.username)
    else:
        form = UserForm(instance=request.user)

    context = {'form': form}
    return render(request, template, context)


class BlogUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = CreateForm
    template_name = 'blog/create.html'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        if request.user != self.object.author:
            return redirect('blog:post_detail', pk=self.object.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('blog:post_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        category = form.cleaned_data.get('category')
        location = form.cleaned_data.get('location')

        if category and not category.is_published:
            form.add_error('category', 'Выбранная категория не опубликована')
            return self.form_invalid(form)

        if location and not location.is_published:
            form.add_error(
                'location',
                'Выбранное местоположение не опубликовано')
            return self.form_invalid(form)

        return super().form_valid(form)


@login_required
def edit_comment(request, pk1, pk2):
    template = 'blog/comment.html'

    comment = get_object_or_404(Comment, pk=pk2)
    post = get_object_or_404(Post, pk=pk1)

    if comment.post != post:
        return redirect('blog:post_detail', pk=pk1)

    if request.user != comment.author:
        return redirect('blog:post_detail', pk=pk1)

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', pk=pk1)
    else:
        form = CommentForm(instance=comment)

    context = {
        'form': form,
        'comment': comment,
        'post': post
    }
    return render(request, template, context)


class BlogCommentDeleteView(DeleteView):
    model = Comment
    template_name = 'blog/comment.html'

    def get_object(self, queryset=None):
        pk1 = self.kwargs.get('pk1')
        pk2 = self.kwargs.get('pk2')
        post = get_object_or_404(Post, pk=pk1)
        comment = get_object_or_404(Comment, pk=pk2, post=post)
        return comment

    def get_success_url(self):
        post_id = self.kwargs.get('pk1')
        return reverse_lazy('blog:post_detail', kwargs={'pk': post_id})

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user != self.object.author:
            return redirect('blog:post_detail', pk=self.object.pk)

        return super().dispatch(request, *args, **kwargs)


class BlogPostDeleteView(DeleteView):
    model = Post
    template_name = 'blog/create.html'

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')
        post = get_object_or_404(Post, pk=pk)
        return post

    def get_success_url(self):
        return reverse_lazy('blog:index')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user != self.object.author:
            return redirect('blog:post_detail', pk=self.object.pk)

        return super().dispatch(request, *args, **kwargs)
