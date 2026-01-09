from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Comment, Post, Category, Location
User = get_user_model()


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email',)


class CreateForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_published=True),
        empty_label="Выберите категорию",
        label="Категория",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    location = forms.ModelChoiceField(
        queryset=Location.objects.filter(is_published=True),
        empty_label="Выберите местоположение (необязательно)",
        label="Местоположение",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )

    pub_date = forms.DateTimeField(
        label='Дата и время публикации',
        initial=timezone.now,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        }),
        help_text='''Если установить дату и время в будущем —
можно делать отложенные публикации.'''
    )

    image = forms.ImageField(
        label='Фото',
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Post
        fields = ['title', 'text', 'category', 'location', 'pub_date', 'image']

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите заголовок публикации'
            }),
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 7,
                'placeholder': 'Текст публикации...'
            }),
        }

        labels = {
            'title': 'Заголовок',
            'text': 'Текст',
        }

        help_texts = {
            'title': 'Название вашей публикации',
            'text': 'Основное содержание публикации',
        }

    def clean_pub_date(self):
        """Валидация даты публикации"""
        pub_date = self.cleaned_data.get('pub_date')

        if pub_date and pub_date < timezone.now():
            pass

        return pub_date

    def save(self, commit=True, author=None):
        """Сохраняем пост с автором"""
        post = super().save(commit=False)
        if author:
            post.author = author
        post.is_published = True

        if commit:
            post.save()
            self.save_m2m()

        return post
