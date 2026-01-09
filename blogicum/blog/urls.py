from django.urls import path

from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.BlogListView.as_view(), name='index'),
    path('posts/<int:pk>/', views.BlogPostDetailView.as_view(),
         name='post_detail'),
    path('category/<slug:category_slug>/',
         views.CategoryPostsListView.as_view(), name='category_posts'),
    path('posts/create/', views.PostCreateView.as_view(), name='create_post'),
    path('posts/<int:pk>/edit/', views.BlogUpdateView.as_view(),
         name='edit_post'),
    path('posts/<int:pk>/delete/', views.BlogPostDeleteView.as_view(),
         name='delete_post'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/', views.UserProfileView.as_view(),
         name='profile'),
    path('posts/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('posts/<int:pk1>/edit_comment/<int:pk2>/', views.edit_comment,
         name='edit_comment'),
    path('posts/<int:pk1>/delete_comment/<int:pk2>/',
         views.BlogCommentDeleteView.as_view(), name='delete_comment')
]
