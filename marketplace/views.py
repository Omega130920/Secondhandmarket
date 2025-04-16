from urllib import request
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import UserRegistrationForm, PinVerificationForm, ItemForm, ContactSellerForm
from .models import Item, Notification, Message, ItemTransaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Prefetch, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import uuid
import os
import random
import string
from django import forms
from .models import Notification, Message, Item, ItemTransaction  # Changed Transaction to ItemTransaction

@login_required
def mark_notification_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save()
    return redirect('user_dashboard')

@login_required
def mark_as_read(request, message_id):
    message = get_object_or_404(Message, id=message_id, recipient=request.user)
    if not message.is_read:
        message.is_read = True
        message.save()
    return redirect('user_dashboard')

@login_required
def user_dashboard(request):
    # Messages received by the user (excluding those they sent that were accepted)
    received_messages = Message.objects.filter(recipient=request.user).exclude(sender=request.user, is_accepted=True).order_by('-sent_at')
    unread_messages_count = received_messages.filter(is_read=False).count()

    # Notifications for the user
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    unread_notifications_count = notifications.filter(is_read=False).count()

    # Items for which the user (the sender of the initial message) has been chosen as the buyer and payment is pending
    items_to_pay = Item.objects.filter(
        message__sender=request.user,
        message__is_accepted=True,
        message__payment_processed=False
    ).prefetch_related('message_set').distinct()
    awaiting_payment_count = items_to_pay.count()

    # Prepare messages for items awaiting payment
    items_awaiting_payment_with_messages = []
    for item in items_to_pay:
        relevant_messages = item.message_set.filter(
            sender=request.user,
            is_accepted=True,
            payment_processed=False
        )
        items_awaiting_payment_with_messages.append({'item': item, 'messages': relevant_messages})

    # Purchase History (Corrected)
    purchase_history = ItemTransaction.objects.filter(
        buyer=request.user,
        payment_timestamp__isnull=False,   # Payment made
        pin_verified=True,                 # PIN verified
        #funds_released=True               # You can add this if you track funds released
    ).order_by('-payment_timestamp').select_related('item', 'seller')
    purchase_history_count = purchase_history.count()

    # My Listings
    my_listings = Item.objects.filter(seller=request.user).order_by('-created_at')
    my_listings_count = my_listings.count()

    received_messages_with_cancellation_status = []
    for message in received_messages:
        buyer_cancelled_notification_exists = message.notification_set.filter(notification_type='buyer_cancelled').exists()
        received_messages_with_cancellation_status.append({
            'message': message,
            'buyer_cancelled': buyer_cancelled_notification_exists,
        })

    context = {
        'received_messages_with_cancellation_status': received_messages_with_cancellation_status,
        'unread_messages_count': unread_messages_count,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'items_to_pay': items_awaiting_payment_with_messages,
        'awaiting_payment_count': awaiting_payment_count,
        'purchase_history': purchase_history,
        'purchase_history_count': purchase_history_count,
        'my_listings': my_listings,
        'my_listings_count': my_listings_count,
    }
    return render(request, 'marketplace/user_dashboard.html', context)
@login_required
def choose_buyer(request, message_id):
    message = get_object_or_404(Message, id=message_id, recipient=request.user, is_accepted=False)
    item = message.item
    buyer = message.sender

    if request.method == 'POST':
        # Mark the selected message as accepted
        message.is_accepted = True
        message.save()

        # Mark all *other* accepted messages for this *item* as not accepted.
        # This ensures only one buyer is accepted at a time for a specific item.
        Message.objects.filter(item=item, is_accepted=True).exclude(id=message.id).update(is_accepted=False)

        # Create a notification for the chosen buyer
        Notification.objects.create(
            recipient=buyer,
            message=message,
            notification_type='buyer_chosen'
        )

        messages.success(request, f"You have chosen {buyer.username} as the buyer for '{item.title}'. They have been notified.")
        return redirect('user_dashboard')

    return redirect('user_dashboard')

@login_required
def contact_seller(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    seller = item.seller

    if request.method == 'POST':
        form = ContactSellerForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            body = form.cleaned_data['body']
            message = Message(
                sender=request.user,
                recipient=seller,
                item=item,
                subject=subject,
                body=body
            )
            message.save()

            # Create a notification for the seller
            Notification.objects.create(
                recipient=seller,
                message=message,
                notification_type='message_received'
            )

            return redirect('item_detail', item_id=item_id)
    else:
        form = ContactSellerForm()

    context = {'form': form, 'item': item, 'seller': seller}
    return render(request, 'marketplace/contact_seller.html', context)

def item_list_view(request):
    item_list = Item.objects.all().order_by('-created_at')
    per_page = 12
    paginator = Paginator(item_list, per_page)

    page = request.GET.get('page')
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        items = paginator.page(1)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)

    print(f"Type of 'items' in view: {type(items)}")
    print(f"'items.has_previous' in view: {hasattr(items, 'has_previous')}")
    print(f"'items.has_next' in view: {hasattr(items, 'has_next')}")
    print(f"'items.number' in view: {getattr(items, 'number', 'N/A')}")
    print(f"'items.paginator.num_pages' in view: {getattr(items.paginator, 'num_pages', 'N/A') if hasattr(items, 'paginator') else 'N/A'}")
    print(f"Number of items in item_list queryset: {item_list.count()}")
    print(f"Paginator per_page: {paginator.per_page}") # Add this line
    print(f"Paginator count: {paginator.count}")       # Add this line

    context = {'items': items}
    return render(request, 'marketplace/item_list.html', context)

def item_detail_view(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    is_buyer = False
    if request.user.is_authenticated:
        is_buyer = Message.objects.filter(
            item=item,
            sender=request.user,
            is_accepted=True,
            payment_processed=True
        ).exists()

    context = {
        'item': item,
        'is_buyer': is_buyer,
    }
    return render(request, 'marketplace/item_detail.html', context)

@login_required
def list_item(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)  # Include request.FILES for image uploads
        if form.is_valid():
            item = form.save(commit=False)
            item.seller = request.user  # Set the seller to the logged-in user
            item.save()
            return redirect('home')  # Redirect to the homepage or a success page
    else:
        form = ItemForm()
    return render(request, 'marketplace/list_item.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save() # The save method in the form now handles UserProfile creation
            login(request, user)
            return redirect('some_success_url') # Redirect to a success page
    else:
        form = UserRegistrationForm()
    return render(request, 'registration.html', {'form': form})

def home(request):
    return render(request, 'marketplace/home.html')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')  # Redirect to the homepage after login
            else:
                # Display an error message if authentication fails
                form.add_error(None, 'Invalid username or password')
    else:
        form = AuthenticationForm()
    return render(request, 'marketplace/login.html', {'form': form})

@login_required
def choose_buyer(request, message_id):
    message = get_object_or_404(Message, id=message_id, recipient=request.user, is_accepted=False)
    item = message.item

    if request.method == 'POST':
        message.is_accepted = True
        message.save()

        # Optionally, notify the chosen buyer (we'll implement this later)
        messages.success(request, f"You have chosen {message.sender.username} as the buyer for '{item.title}'.")

        # Optionally, you might want to mark other requests for the same item as rejected
        # messages_to_reject = Message.objects.filter(item=item, is_accepted=False).exclude(id=message.id)
        # for msg in messages_to_reject:
        #     # Implement a way to notify these users later if needed
        #     pass

        return redirect('user_dashboard')

    # Should not reach here with a GET request, but just in case
    return redirect('user_dashboard')

@login_required
def choose_buyer(request, message_id):
    message = get_object_or_404(Message, id=message_id, recipient=request.user, is_accepted=False)
    item = message.item
    buyer = message.sender

    if request.method == 'POST':
        # Mark the selected message as accepted
        message.is_accepted = True
        message.save()

        # Mark all *other* accepted messages for this *item* as not accepted.
        # This ensures only one buyer is accepted at a time for a specific item.
        Message.objects.filter(item=item, is_accepted=True).exclude(id=message.id).update(is_accepted=False)

        # Create a notification for the chosen buyer
        Notification.objects.create(
            recipient=buyer,
            message=message,
            notification_type='buyer_chosen'
        )

        messages.success(request, f"You have chosen {buyer.username} as the buyer for '{item.title}'. They have been notified.")
        return redirect('user_dashboard')

    return redirect('user_dashboard')

# We'll need a way to temporarily store registration data and the PIN.
# For simplicity in this example, we can use a dictionary in memory.
# In a production environment, you'd want to use a more robust method
# like Django's cache or a temporary model.
TEMP_REGISTRATION_DATA = {}

def generate_random_pin(length=6):
    characters = string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def register_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            cell_phone = form.cleaned_data['cell_phone']
            id_document = request.FILES['id_document']
            password = form.cleaned_data['password']

            if User.objects.filter(email=email).exists():
                messages.error(request, "An account with this email address already exists.")
                return render(request, 'marketplace/register.html', {'form': form})

            pin = generate_random_pin()

            TEMP_REGISTRATION_DATA[email] = {
                'first_name': first_name,
                'last_name': last_name,
                'cell_phone': cell_phone,
                'id_document_name': id_document.name,
                'id_document_content': id_document.read(),
                'password': password,
                'pin': pin,
                'pin_expiry': timezone.now() + timezone.timedelta(minutes=10)
            }

            subject = 'Your Account Verification PIN'
            message = f'Your PIN is: {pin}. This PIN will expire in 10 minutes.'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]
            send_mail(subject, message, from_email, recipient_list)

            # Store the email in the session to use in the verify_pin view
            request.session['registration_email'] = email

            return redirect('verify_pin')
    else:
        form = UserRegistrationForm()
    return render(request, 'marketplace/register.html', {'form': form})

def verify_pin(request):
    if request.method == 'POST':
        form = PinVerificationForm(request.POST)
        if form.is_valid():
            pin_submitted = form.cleaned_data['pin']
            email = request.session.get('registration_email') # We need to store this in session

            if email in TEMP_REGISTRATION_DATA:
                registration_data = TEMP_REGISTRATION_DATA[email]
                if timezone.now() < registration_data['pin_expiry'] and pin_submitted == registration_data['pin']:
                    # Create the user
                    user = User.objects.create_user(
                        username=email.split('@')[0],  # Basic username
                        email=email,
                        password=registration_data['password'],
                        first_name=registration_data['first_name'],
                        last_name=registration_data['last_name']
                    )
                    # Here you would also save the cell phone and ID document
                    # For now, let's just print them
                    print(f"Cell Phone: {registration_data['cell_phone']}")
                    print(f"ID Document Name: {registration_data['id_document_name']}")
                    # In a real app, save the ID document to MEDIA_ROOT

                    messages.success(request, "Registration successful! You can now log in.")
                    del TEMP_REGISTRATION_DATA[email] # Clean up temporary data
                    return redirect('login')
                else:
                    messages.error(request, "Invalid or expired PIN.")
            else:
                messages.error(request, "No registration data found for this email.")
    else:
        form = PinVerificationForm()
        # We need to get the email from the previous step to associate the PIN
        # For now, we'll just render the form. We'll refine this flow later.
        # A better approach might be to pass the email in the redirect or use session.
        email_in_session = request.session.get('registration_email')
        return render(request, 'marketplace/verify_pin.html', {'form': form, 'email': email_in_session})

    # If POST fails or PIN is invalid, re-render the form
    email_in_session = request.session.get('registration_email')
    return render(request, 'marketplace/verify_pin.html', {'form': form, 'email': email_in_session})

@login_required
def process_payment(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    try:
        accepted_message = Message.objects.get(
            item=item,
            recipient=item.seller,
            sender=request.user,
            is_accepted=True,
            payment_processed=False
        )

        if request.method == 'POST':
            # Simulate payment processing
            accepted_message.payment_processed = True
            accepted_message.save()

            # Generate a unique PIN
            verification_pin = str(random.randint(100000, 999999))  # 6-digit PIN

            # Create ItemTransaction (Crucial for tracking)
            transaction = ItemTransaction.objects.create(
                item=item,
                buyer=request.user,
                seller=item.seller,
                transaction_id=f"TRANS_{random.randint(100000, 999999)}",
                payment_timestamp=timezone.now(),
                verification_pin=verification_pin,
                pin_verified=False
            )

            # Send message to buyer with the PIN
            Message.objects.create(
                sender=item.seller,
                recipient=request.user,
                subject=f'Payment Confirmed for "{item.title}" - Your Verification PIN',
                body=(
                    f'Your payment for "{item.title}" (Transaction ID: {transaction.transaction_id}) has been confirmed. '
                    f'Your verification PIN is: {verification_pin}\n\nPlease provide this PIN to the seller upon handover.'
                ),
                item=item
            )
            Notification.objects.create(
                recipient=request.user,
                message=accepted_message,
                notification_type='payment_confirmed_pin_sent'
            )


            # Send message to seller with the verification link
            verification_link = reverse('enter_verification_pin', kwargs={'transaction_id': transaction.transaction_id})
            Message.objects.create(
                sender=request.user,
                recipient=item.seller,
                subject=f'Action Required: Verify Collection PIN for "{item.title}"',
                body=(
                    f'The buyer has completed payment for "{item.title}" (Transaction ID: {transaction.transaction_id}). '
                    f'Once you receive the verification PIN from the buyer, please enter it here: {request.build_absolute_uri(verification_link)}'
                ),
                item=item
            )
            Notification.objects.create(
                recipient=item.seller,
                message=accepted_message,
                notification_type='pin_verification_required'
            )

            messages.success(request, f'Payment for "{item.title}" processed. A verification PIN has been sent to you. The seller has been asked to provide collection details and verify the PIN.')
            return redirect('user_dashboard')

        else:
            context = {'item': item, 'accepted_message': accepted_message}
            return render(request, 'marketplace/process_payment.html', context)

    except Message.MultipleObjectsReturned:
        messages.error(request, "Error: Multiple accepted offers found for this item for you. Please contact support.")
        return redirect('user_dashboard')
    except Message.DoesNotExist:
        messages.error(request, "Error: No accepted offer found for this item for you.")
        return redirect('user_dashboard')

    
@login_required
def add_item(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.seller = request.user
            item.save()
            return redirect('item_detail', item.id)
    else:
        form = ItemForm()
    return render(request, 'marketplace/add_item.html', {'form': form})

@login_required
def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id, seller=request.user)
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('item_detail', item.id)
    else:
        form = ItemForm(instance=item)
    return render(request, 'marketplace/edit_item.html', {'form': form, 'item': item})

def generate_unique_barcode_string():
    return uuid.uuid4().hex

@login_required
def buyer_confirms_payment(request, message_id):
    message = get_object_or_404(
        Message,
        pk=message_id,
        sender=request.user,  # The current user (buyer) was the sender
        is_accepted=True,
        payment_processed=False
    )
    item = message.item
    seller = item.seller
    buyer = request.user

    if request.method == 'POST':
        # Simulate payment processing
        message.payment_processed = True
        message.transaction_id = f"TRANS_{random.randint(100000, 999999)}"
        message.save()
        messages.success(request, f'Payment for "{item.title}" processed. Transaction ID: {message.transaction_id}. You will receive a PIN for verification shortly.')

        # Generate a unique PIN
        pin = str(random.randint(100000, 999999))  # 6-digit PIN

        # Store the transaction details with the PIN
        ItemTransaction.objects.create(
            item=item,
            buyer=buyer,
            seller=seller,
            transaction_id=message.transaction_id,
            payment_timestamp=timezone.now(),
            verification_pin=pin,
            pin_verified=False
        )

        # Send a message to the seller with the verification link
        verification_link = reverse('enter_verification_pin', kwargs={'transaction_id': message.transaction_id})
        seller_message = Message.objects.create(
            sender=buyer,
            recipient=seller,
            item=item,
            subject=f'Action Required: Verify Collection PIN for "{item.title}"',
            body=(
                f'The buyer has completed payment for "{item.title}" (Transaction ID: {message.transaction_id}). '
                f'Once you receive the verification PIN from the buyer or collection service, please enter it here: '
                f'{request.build_absolute_uri(verification_link)}'
            )
        )

        # Notify the seller about the PIN verification link
        Notification.objects.create(
            recipient=seller,
            message=seller_message,
            notification_type='pin_verification_required'
        )

        # Optionally, send the PIN to the buyer (and collection service - you'll need to handle this part)
        buyer_message = Message.objects.create(
            sender=seller,  # Sending from seller's perspective for confirmation
            recipient=buyer,
            item=item,
            subject=f'Payment Confirmed for "{item.title}" - Your Verification PIN',
            body=(
                f'Your payment for "{item.title}" (Transaction ID: {message.transaction_id}) has been confirmed. '
                f'Your verification PIN is: {pin}\n\n'
                f'Please provide this PIN to the seller or the collection service upon handover.'
            )
        )
        Notification.objects.create(
            recipient=buyer,
            message=buyer_message,
            notification_type='payment_confirmed_pin_sent'
        )

        messages.info(request, f'Payment confirmed. A verification PIN has been sent to you. The seller has been asked to provide collection details and verify the PIN.')
        return redirect('user_dashboard')

    return render(request, 'marketplace/confirm_payment.html', {'message': message})

@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Message, id=message_id, recipient=request.user) # Or sender, depending on who should view
    return render(request, 'marketplace/message_detail.html', {'message': message})

class VerificationPinForm(forms.Form):
    verification_pin = forms.CharField(max_length=6, label='Verification PIN')

@login_required
def enter_verification_pin(request, transaction_id):
    transaction = get_object_or_404(ItemTransaction, transaction_id=transaction_id, seller=request.user, pin_verified=False)

    if request.method == 'POST':
        form = VerificationPinForm(request.POST)
        if form.is_valid():
            entered_pin = form.cleaned_data['verification_pin']
            if entered_pin == transaction.verification_pin:
                transaction.pin_verified = True
                transaction.save()

                # Notify buyer of successful verification
                Message.objects.create(
                    sender=request.user, # Seller is sending the verification message
                    recipient=transaction.buyer,
                    subject=f'PIN Verified for "{transaction.item.title}"',
                    body=f'The verification PIN for your purchase of "{transaction.item.title}" has been successfully verified by the seller.',
                    item=transaction.item
                )
                Notification.objects.create(
                    recipient=transaction.buyer,
                    #message=None,  # Or a general notification
                    notification_type='pin_verified'
                )

                messages.success(request, f'PIN verified for Transaction ID: {transaction.transaction_id}.')
                # Here you would add logic to trigger the release of funds
                # For the simulated payment, you might just want to update a status
                # or send another notification.
                return redirect('user_dashboard')
            else:
                messages.error(request, 'Incorrect PIN. Please try again.')
        else:
            messages.error(request, 'Invalid PIN format.')
    else:
        form = VerificationPinForm()

    return render(request, 'marketplace/enter_verification_pin.html', {'form': form, 'transaction_id': transaction_id})

@login_required
def cancel_purchase(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    # Check if the logged-in user is the chosen buyer for this item
    relevant_message = Message.objects.filter(
        item=item,
        sender=request.user,
        is_accepted=True,
        payment_processed=False
    ).first()

    if relevant_message:
        # Reset the message status
        relevant_message.is_accepted = False
        relevant_message.payment_processed = False
        relevant_message.save()

        # Notify the seller about the cancellation
        seller_notification = Notification.objects.create(
            recipient=item.seller,
            notification_type='buyer_cancelled',
            message=relevant_message  # Link to the original interaction
        )

        messages.success(request, f"Your purchase for '{item.title}' has been cancelled.")
        return redirect('user_dashboard')
    else:
        messages.error(request, "You are not the chosen buyer for this item or the purchase cannot be cancelled at this stage.")
        return redirect('user_dashboard')