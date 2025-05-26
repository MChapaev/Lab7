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
            if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Record created successfully'})
            return redirect('index')
        else:
            errors = {**client_form.errors, **policy_form.errors, **claim_form.errors}
            if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
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
            if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': f'Client {client_id} deleted'})
            return redirect('index')
        else:
            if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = DeleteClientForm()

    return render(request, 'delete.html', {'form': form})


def view_records(request):
    query_type = request.GET.get('query_type', '')
    if request.method == 'POST' and 'HTTP_X_REQUESTED_WITH' in request.META and request.META[
        'HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
        query_type = request.POST.get('query_type', '')
    results = []
    columns = []
    title = ''

    print('Request META:', {k: v for k, v in request.META.items() if
                            k.startswith('HTTP_') or k in ['REQUEST_METHOD', 'PATH_INFO', 'REMOTE_ADDR']})
    is_ajax = 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest'
    print('Is AJAX:', is_ajax)
    print('Query Type:', query_type)

    if query_type == 'by_client':
        full_name = request.GET.get('full_name', '').strip()
        passport = request.GET.get('passport_number', '').strip()
        if full_name and passport and request.method == 'GET' and not is_ajax:
            results = Claim.objects.filter(
                policy__client__full_name=full_name,
                policy__client__passport_number=passport
            ).values(
                'description', 'claim_date', 'amount', 'policy__policy_type'
            )
            columns = ['Description', 'Claim Date', 'Amount', 'Policy Type']
            title = f"Claims for {full_name} ({passport})"
        elif request.method == 'POST' and is_ajax:
            print('Processing AJAX request for by_client')
            full_name = request.POST.get('full_name', '').strip()
            passport = request.POST.get('passport_number', '').strip()
            print('Full Name:', full_name, 'Passport:', passport)
            if full_name and passport:
                results = Claim.objects.filter(
                    policy__client__full_name=full_name,
                    policy__client__passport_number=passport
                ).values(
                    'description', 'claim_date', 'amount', 'policy__policy_type'
                )
                columns = ['Description', 'Claim Date', 'Amount', 'Policy Type']
                title = f"Claims for {full_name} ({passport})"
                # Преобразуем даты в строковый формат
                formatted_results = []
                for item in results:
                    formatted_item = dict(item)
                    if formatted_item['claim_date']:
                        formatted_item['claim_date'] = formatted_item['claim_date'].strftime('%Y-%m-%d')
                    formatted_results.append(formatted_item)
                response_data = {
                    'success': True,
                    'results': formatted_results,
                    'columns': columns,
                    'title': title
                }
                print('Returning JSON:', response_data)
                return JsonResponse(response_data)
            else:
                error_response = {'success': False, 'message': 'Full name and passport number are required'}
                print('Returning error JSON:', error_response)
                return JsonResponse(error_response, status=400)

    elif query_type == 'active':
        results = Claim.objects.filter(
            policy__end_date__gte=date.today()
        ).values(
            'description', 'claim_date', 'amount', 'policy__policy_type', 'policy__end_date'
        )
        # Преобразуем даты в строковый формат
        formatted_results = []
        for item in results:
            formatted_item = dict(item)
            if formatted_item['claim_date']:
                formatted_item['claim_date'] = formatted_item['claim_date'].strftime('%Y-%m-%d')
            if formatted_item['policy__end_date']:
                formatted_item['policy__end_date'] = formatted_item['policy__end_date'].strftime('%Y-%m-%d')
            formatted_results.append(formatted_item)
        results = formatted_results
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

    # Преобразуем ключи в словаре для соответствия именам столбцов
    formatted_results = []
    for row in results:
        formatted_row = {}
        for col in columns:
            key = col.lower().replace(' ', '_')
            if key in row:
                formatted_row[col] = row[key]
        formatted_results.append(formatted_row)

    if request.GET.get('export') == 'json':
        data = list(results)
        response = HttpResponse(
            content_type='application/json',
            headers={'Content-Disposition': f'attachment; filename="{title.replace(" ", "_")}.json"'}
        )
        json.dump(data, response, indent=2)
        return response

    print('Rendering HTML response')
    return render(request, 'view.html', {
        'results': formatted_results,
        'columns': columns,
        'title': title
    })