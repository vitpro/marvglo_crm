import registration
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET, require_POST
import Queue

from marvglo.models import Employee, SaleItem, Transaction
from marvglo_crm.settings import MAX_EMPLOYEE_LEVEL, PERSONAL_BONUS_COMMISSION, VOLUME_BONUS_COMMISSION


@require_GET
def index(request):
    if not request.user.is_authenticated:
        ctx = {
            'isAuthenticated': request.user.is_authenticated,
        }
        return render(request, 'marvglo/home.html', ctx)

    # Collect transactions for lower levels
    employee = request.user.employee
    transactions = []
    transactions.extend(list(employee.transaction_set.all()))
    subEmployeeQueue = Queue.PriorityQueue()
    for sub_emp in list(employee.employee_set.all()):
        subEmployeeQueue.put(sub_emp)
    while not subEmployeeQueue.empty():
        sub_employee = subEmployeeQueue.get()
        transactions.extend(list(sub_employee.transaction_set.all()))
        for sub_emp in list(sub_employee.employee_set.all()):
            subEmployeeQueue.put(sub_emp)

    # calculate commissions
    personal_bonuses = []
    volume_bonuses = []
    for transaction_id in range(len(transactions)):
        for level in range(MAX_EMPLOYEE_LEVEL):
            personal_bonuses.append(
                PERSONAL_BONUS_COMMISSION[level] * transactions[transaction_id].quantity * transactions[
                    transaction_id].sold_at_price)
            volume_bonuses.append(transactions[transaction_id].quantity * transactions[transaction_id].sold_at_price *
                                  VOLUME_BONUS_COMMISSION[level][transactions[transaction_id].owner.level])
        transactions[transaction_id].personal_bonus = personal_bonuses
        transactions[transaction_id].volume_bonus = volume_bonuses
        personal_bonuses = []
        volume_bonuses = []

    ctx = {
        'employee': request.user.employee,
        'isAuthenticated': request.user.is_authenticated,
        'adminApproved': employee.admin_approved,
        'transactions': transactions,
        'items': list(SaleItem.objects.all())
    }
    return render(request, 'marvglo/home.html', ctx)


@receiver(registration.signals.user_registered)
def register_new_player(sender, **kwargs):
    employee = Employee(user=kwargs['user'])
    employee.save()


@login_required(login_url='reg/login/')
@require_GET
def remove_transaction(request, transaction_id):
    try:
        t = Transaction.objects.get(id=transaction_id)
        # check transaction ownership
        if t.owner == request.user.employee:
            t.delete()
    except Transaction.DoesNotExist:
        # did not even exist
        pass
    return redirect(index)


@login_required(login_url='reg/login/')
@require_GET
def view_transaction(request, transaction_id):
    ctx = {
        'employee': request.user.employee,
        'isAuthenticated': request.user.is_authenticated,
        'adminApproved': request.user.employee.admin_approved,
        'items': list(SaleItem.objects.all())
    }
    try:
        t = Transaction.objects.get(id=transaction_id)
        # check transaction ownership
        if t.owner != request.user.employee:
            return redirect(index)
        ctx['transaction'] = t
    except Transaction.DoesNotExist:
        # did not even exist
        return redirect(index)
    return render(request, 'marvglo/transaction.html', ctx)


@require_POST
def submit_transaction(request):
    t = Transaction(item=SaleItem.objects.get(name=request.POST['itemName']),
                    quantity=request.POST['quantity'],
                    owner=request.user.employee,
                    sold_at_price=SaleItem.objects.get(name=request.POST['itemName']).price)
    t.save()
    return redirect(index)


@require_POST
def amend_transaction(request, transaction_id):
    try:
        t = Transaction.objects.get(id=transaction_id)
        # check transaction ownership
        if t.owner == request.user.employee:
            t.item = SaleItem.objects.get(name=request.POST['itemName'])
            t.quantity = request.POST['quantity']
            t.save()
    except Transaction.DoesNotExist:
        # did not even exist
        pass
    return redirect(index)


@login_required(login_url='reg/login/')
def manage(request):
    if request.method == 'GET':
        employees = Employee.objects.filter(admin_approved=False)
        ctx = {
            'employee': request.user.employee,
            'isAuthenticated': request.user.is_authenticated,
            'any_unassigned': len(list(employees)) != 0,
            'unassigned_employees': list(employees),
            'managers': list(Employee.objects.filter(level__lte=2))  # those who can manage lowest level employees
        }
        return render(request, 'marvglo/manage.html', ctx)
    else:
        try:
            employee = Employee.objects.get(user=User.objects.get(username=request.POST['employee']))
            manager = Employee.objects.get(user=User.objects.get(username=request.POST['manager']))
            employee.boss = manager
            employee.admin_approved = True
            employee.save()
        except:
            #shit
            pass
        return redirect(manage)

