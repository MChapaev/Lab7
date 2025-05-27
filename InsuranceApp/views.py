from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from .models import Client, Policy, Claim
from .forms import ClientForm, PolicyForm, ClaimForm, DeleteClientForm
from django.db.models import Count, Sum
from django.core.serializers import serialize
from datetime import date
import json

def index(request):
    try:
        policy_types = Policy.objects.values('policy_type').distinct()
    except Exception as e:
        print(f"Error fetching policy types: {str(e)}")
        policy_types = []
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
    is_ajax = 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest'
    query_type = request.POST.get('query_type', '') if is_ajax else request.GET.get('query_type', '')

    print('Request META:', {k: v for k, v in request.META.items() if k.startswith('HTTP_') or k in ['REQUEST_METHOD', 'PATH_INFO', 'REMOTE_ADDR']})
    print('Is AJAX:', is_ajax)
    print('Query Type:', query_type)

    if request.method == 'POST' and is_ajax:
        if query_type == 'by_client':
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
                columns = ['Описание', 'Дата претензии', 'Сумма', 'Тип полиса']
                title = f"Претензии для {full_name} ({passport})"
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
                error_response = {'success': False, 'message': 'ФИО и номер паспорта обязательны.'}
                print('Returning error JSON:', error_response)
                return JsonResponse(error_response, status=400)

        elif query_type == 'active':
            results = Claim.objects.filter(
                policy__end_date__gte=date.today()
            ).values(
                'description', 'claim_date', 'amount', 'policy__policy_type', 'policy__end_date'
            )
            formatted_results = []
            for item in results:
                formatted_item = dict(item)
                if formatted_item['claim_date']:
                    formatted_item['claim_date'] = formatted_item['claim_date'].strftime('%Y-%m-%d')
                if formatted_item['policy__end_date']:
                    formatted_item['policy__end_date'] = formatted_item['policy__end_date'].strftime('%Y-%m-%d')
                formatted_results.append(formatted_item)
            columns = ['Описание', 'Дата претензии', 'Сумма', 'Тип полиса', 'Дата окончания полиса']
            title = 'Активные претензии (Полис не истёк)'
            response_data = {
                'success': True,
                'results': formatted_results,
                'columns': columns,
                'title': title
            }
            print('Returning JSON for active claims:', response_data)
            return JsonResponse(response_data)

        elif query_type == 'group_by_type':
            results = Claim.objects.values(
                'policy__policy_type'
            ).annotate(
                claim_count=Count('id'),
                total_amount=Sum('amount')
            )
            columns = ['Тип полиса', 'Количество претензий', 'Общая сумма']
            title = 'Претензии, сгруппированные по типу полиса'
            response_data = {
                'success': True,
                'results': list(results),
                'columns': columns,
                'title': title
            }
            print('Returning JSON for group_by_type:', response_data)
            return JsonResponse(response_data)

        else:
            return JsonResponse({'success': False, 'message': 'Неверный тип запроса.'}, status=400)

    if request.GET.get('export') == 'json':
        results = []
        columns = []
        title = ''
        query_type = request.GET.get('query_type', '')

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
                columns = ['Описание', 'Дата претензии', 'Сумма', 'Тип полиса']
                title = f"Претензии для {full_name} ({passport})"

        elif query_type == 'active':
            results = Claim.objects.filter(
                policy__end_date__gte=date.today()
            ).values(
                'description', 'claim_date', 'amount', 'policy__policy_type', 'policy__end_date'
            )
            columns = ['Описание', 'Дата претензии', 'Сумма', 'Тип полиса', 'Дата окончания полиса']
            title = 'Активные претензии (Полис не истёк)'

        elif query_type == 'group_by_type':
            results = Claim.objects.values(
                'policy__policy_type'
            ).annotate(
                claim_count=Count('id'),
                total_amount=Sum('amount')
            )
            columns = ['Тип полиса', 'Количество претензий', 'Общая сумма']
            title = 'Претензии, сгруппированные по типу полиса'

        formatted_results = []
        for row in results:
            formatted_row = dict(row)
            for key in formatted_row:
                if isinstance(formatted_row[key], date):
                    formatted_row[key] = formatted_row[key].strftime('%Y-%m-%d')
            formatted_results.append(formatted_row)

        data = list(formatted_results)
        response = HttpResponse(
            content_type='application/json',
            headers={'Content-Disposition': f'attachment; filename="{title.replace(" ", "_")}.json"'}
        )
        json.dump(data, response, indent=2)
        return response

    return render(request, 'view.html', {})

def update_user(request):
    is_ajax = 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest'
    
    if request.method == 'POST' and is_ajax:
        action = request.POST.get('action', '')
        
        if action == 'search':
            full_name = request.POST.get('full_name', '').strip()
            passport_number = request.POST.get('passport_number', '').strip()
            
            if not full_name or not passport_number:
                return JsonResponse({'success': False, 'message': 'ФИО и номер паспорта обязательны.'}, status=400)
            
            try:
                client = Client.objects.get(full_name=full_name, passport_number=passport_number)
                response_data = {
                    'success': True,
                    'user': {
                        'full_name': client.full_name,
                        'birth_date': client.birth_date.strftime('%Y-%m-%d') if client.birth_date else '',
                        'passport_number': client.passport_number,
                        'phone': client.phone if client.phone else '',
                        'email': client.email if client.email else ''
                    }
                }
                return JsonResponse(response_data)
            except Client.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Пользователь не найден.'})
        
        elif action == 'update':
            full_name_original = request.POST.get('full_name_original', '').strip()
            passport_number_original = request.POST.get('passport_number_original', '').strip()
            full_name_new = request.POST.get('full_name_new', '').strip()
            birth_date_new = request.POST.get('birth_date_new', '').strip()
            passport_number_new = request.POST.get('passport_number_new', '').strip()
            phone_new = request.POST.get('phone_new', '').strip()
            email_new = request.POST.get('email_new', '').strip()
            
            if not all([full_name_original, passport_number_original, full_name_new, passport_number_new]):
                return JsonResponse({'success': False, 'message': 'ФИО и номер паспорта обязательны.'}, status=400)
            
            try:
                client = Client.objects.get(full_name=full_name_original, passport_number=passport_number_original)
                client.full_name = full_name_new
                if birth_date_new:
                    client.birth_date = date.fromisoformat(birth_date_new)
                if phone_new:
                    client.phone = phone_new
                if email_new:
                    client.email = email_new
                client.passport_number = passport_number_new
                client.save()
                return JsonResponse({'success': True, 'message': 'Данные пользователя успешно обновлены.'})
            except Client.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Пользователь не найден.'}, status=404)
            except ValueError as e:
                return JsonResponse({'success': False, 'message': f'Неверный формат даты: {str(e)}'}, status=400)
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'Произошла ошибка: {str(e)}'}, status=500)
    
    return render(request, 'update.html')