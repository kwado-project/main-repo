from rest_framework.pagination import CursorPagination, PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class LedgerCursorPagination(CursorPagination):
    """Cursor pagination for append-only, very large tables (ledgers, logs).

    Unlike OFFSET pagination it stays O(1) deep into the history.
    """

    page_size = 25
    ordering = "-created_at"
