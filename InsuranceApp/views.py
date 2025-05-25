from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from .models import Client, Policy, Claim
from .forms import ClientForm, PolicyForm, ClaimForm, DeleteClientForm
from django.db.models import Count, Sum
from django.core.serializers import serialize
from datetime import date
import json


def index(request):
    policy_types = Policy.objects.values('policy_type').distinct()
    return render(request, 'index.html', {'policy_types': policy_types})


def create_record(request):
    if request.method == 'POST':
        client_form = ClientForm(request.POST)
        policy_form = PolicyForm(request.POST)
        claim_form = ClaimForm(request.POST)

        if client_form.is_valid() and policy_form.is_valid() and claim_form.is_valid():
            client = client_form.save()
            policy = policy_form.save(commit=False)
            policy.client = client
            policy.save()
            claim = claim_form.save(commit=False)
            claim.policy = policy
            claim.save()
            if request.is_ajax():
                return JsonResponse({'success': True, 'message': 'Record created successfully'})
            return redirect('index')
        else:
            errors = {**client_form.errors, **policy_form.errors, **claim_form.errors}
            if request.is_ajax():
                return JsonResponse({'success': False, 'errors': errors}, status=400)
    else:
        client_form = ClientForm()
        policy_form = PolicyForm()
        claim_form = ClaimForm()

    return render(request, 'create.html', {
        'client_form': client_form,
        'policy_form': policy_form,
        'claim_form': claim_form
    })


def delete_client(request):
    if request.method == 'POST':
        form = DeleteClientForm(request.POST)
        if form.is_valid():
            client_id = form.cleaned_data['client_id']
            Client.objects.filter(id=client_id).delete()
            if request.is_ajax():
                return JsonResponse({'success': True, 'message': f'Client {client_id} deleted'})
            return redirect('index')
        else:
            if request.is_ajax():
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = DeleteClientForm()

    return render(request, 'delete.html', {'form': form})


def view_records(request):
    query_type = request.GET.get('query_type', '')
    results = []
    columns = []
    title = ''

    if query_type == 'by_client':
        full_name = request.GET.get('full_name', '').strip()
        passport = request.GET.get('passport_number', '').strip()
        if full_name and passport:
            results = Claim.objects.filter(
                policy__client__full_name=full_name,
                policy__client__passport_number=passport
            ).values(
                'description', 'claim_date', 'amount', 'policy__policy_type'
            )
            columns = ['Description', 'Claim Date', 'Amount', 'Policy Type']
            title = f"Claims for {full_name} ({passport})"

    elif query_type == 'active':
        results = Claim.objects.filter(
            policy__end_date__gte=date.today()
        ).values(
            'description', 'claim_date', 'amount', 'policy__policy_type', 'policy__end_date'
        )
        columns = ['Description', 'Claim Date', 'Amount', 'Policy Type', 'Policy End Date']
        title = 'Active Claims (Policy not expired)'

    elif query_type == 'group_by_type':
        results = Claim.objects.values(
            'policy__policy_type'
        ).annotate(
            claim_count=Count('id'),
            total_amount=Sum('amount')
        )
        columns = ['Policy Type', 'Claim Count', 'Total Amount']
        title = 'Claims Grouped by Policy Type'

    if request.GET.get('export') == 'json':
        data = list(results)
        response = HttpResponse(
            content_type='application/json',
            headers={'Content-Disposition': f'attachment; filename="{title.replace(" ", "_")}.json"'}
        )
        json.dump(data, response, indent=2)
        return response

    return render(request, 'view.html', {
        'results': results,
        'columns': columns,
        'title': title
    })