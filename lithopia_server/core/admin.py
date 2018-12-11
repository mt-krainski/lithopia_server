from django.contrib import admin
from .models import Dataset, RequestImage, ReferenceImage

admin.site.register(Dataset)
admin.site.register(RequestImage)
admin.site.register(ReferenceImage)
