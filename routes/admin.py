from django.contrib import admin

from routes.constants import STATE_MAPPING
from routes.models import Station


# Register your models here.

class StateFilter(admin.SimpleListFilter):
    title = "State"
    parameter_name = "state"

    def lookups(self, request, model_admin):
        return [
            (state_code, state_name)
            for state_code, state_name in STATE_MAPPING.items()
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(state=self.value())

        return queryset


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('opis_id', 'name', 'state_name', 'city', 'price', 'lat', 'lng')
    list_filter = (StateFilter, )
    search_fields = ('opis_id','name', 'city', 'address')
    ordering = ('state', 'city')
    list_per_page = 50

    def state_name(self, obj):
        return f"{STATE_MAPPING.get(obj.state, '')} ({obj.state})"

