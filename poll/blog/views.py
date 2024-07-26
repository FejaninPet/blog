from django.core.mail import send_mail
from django.shortcuts import render, get_object_or_404
from .models import Post, Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from .forms import EmailPostForm, CommentForm, SearchForm
from django.views.decorators.http import require_POST
from taggit.models import Tag
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank


def post_list(request, tag_slug=None):
    post_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])
    # постраничная разбивка
    paginator = Paginator(post_list, 3)  # кол-во объектов
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        # если page_number не цлое число, то вернуть первую страницу
        posts = paginator.page(1)
    except EmptyPage:
        # если вызванная страница находится за пределами существующего диапазона,
        # то вернуть последнюю страницу
        posts = paginator.page(paginator.num_pages)
    return render(request, 'blog/post/list.html',
                  {'posts': posts, 'tag': tag})


# class PostListView(ListView):
#     """
#     Альтернативное представление списка постов
#     """
#     queryset = Post.published.all()
#     context_object_name = 'posts'  # если необъявить, в шаблон будет передана переменная object_list
#     # context_object_name будет передан в шаблон по имени page_obj
#     paginate_by = 3
#    template_name = 'blog/post/list.html'


def post_detail(request, year, month, day, slug):
    post = get_object_or_404(Post,
                             status=Post.Status.PUBLISHED,
                             slug=slug,
                             publish__year=year,
                             publish__month=month,
                             publish__day=day)
    # Список активных комментариев к этому посту
    comments = post.comments.filter(active=True)
    # Форма для комментариея пользователями
    form = CommentForm()
    # Список схожих постов
    # QuerySet имеет метод values_list, к-ый кортежи со значениями заданных полей; flat=True ==>
    # преобразует из [(1,), (2,), ...] => [1, 2, ...]
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]
    return render(request, 'blog/post/detail.html',
                  {'post': post, 'comments': comments, 'form': form, 'similar_posts': similar_posts})


def post_share(request, post_id):
    post = get_object_or_404(Post,
                             id=post_id,
                             status=Post.Status.PUBLISHED)
    sent = False
    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f'{cd["name"]} реккомендует вам прочитать {post.title}'
            message = f'Прочитай "{post.title}" по адресу {post_url}\n\nКомментарий от {cd["name"]}: {cd["comments"]}'
            send_mail(subject, message, 'same@mail.ru', [cd['to']])
            sent = True
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post, 'form': form, 'sent': sent})


@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    comment = None
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # Создать объект класса Comment, не сохраняя его в базе данных
        comment = form.save(commit=False)
        # Назначить пост комментарию
        comment.post = post
        # Сохранить комментарий в базе данных
        comment.save()
    return render(request, 'blog/post/comment.html',
                  {'post': post, 'form': form, 'comment': comment})


def post_search(request):
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            # создание поиска с весами
            # A - 1.0; B - 0.4; C - 0.2; D - 0.1
            query = form.cleaned_data['query']
            search_vector = SearchVector('title', weight='A', config='russian') + \
                            SearchVector('body', weight='B', config='russian')
            search_query = SearchQuery(query, config='russian')
            results = Post.published.annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query)
            ).filter(rank__gte=0.3).order_by('-rank')

    return render(request,
                  'blog/post/search.html',
                  {
                      'form': form,
                      'query': query,
                      'results': results
                  })
