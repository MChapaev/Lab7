from django.contrib import admin
from .models import Client, Policy, Claim

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'passport_number', 'birth_date', 'phone', 'email')
    list_filter = ('birth_date',)
    search_fields = ('full_name', 'passport_number')
    ordering = ('full_name',)

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'policy_type', 'start_date', 'end_date', 'premium')
    list_filter = ('start_date', 'end_date', 'policy_type')
    search_fields = ('policy_type', 'client__full_name')
    ordering = ('start_date',)

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'policy', 'claim_date', 'amount', 'description')
    list_filter = ('claim_date', 'policy__policy_type')
    search_fields = ('description', 'policy__policy_type')
    ordering = ('claim_date',)