from django.core.paginator import Paginator

COUNT = 10


def paginating(request, post_list):
    paginator = Paginator(post_list, COUNT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
