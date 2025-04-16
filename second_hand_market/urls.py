# second_hand_market/urls.py
from django.contrib import admin
from django.urls import path, include  # Import include
from marketplace import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # Include authentication URLs
    path('register/', views.register_user, name='register'),
    path('verify_pin/', views.verify_pin, name='verify_pin'),
    path('login/', views.login_view, name='login'),  # You might have a custom login view
    path('logout/', views.logout_view, name='logout'), # You might have a custom logout view
    path('list_item/', views.list_item, name='list_item'),
    path('item/add/', views.list_item, name='add_item'),  # Reusing list_item view for adding
    path('item/edit/<int:item_id>/', views.edit_item, name='edit_item'), # Add edit item URL
    path('', views.home, name='home'),
    path('item/<int:item_id>/', views.item_detail_view, name='item_detail'),
    path('item_list/', views.item_list_view, name='item_list'),
    path('item/<int:item_id>/contact/', views.contact_seller, name='contact_seller'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('messages/<int:message_id>/read/', views.mark_as_read, name='mark_as_read'),
    path('messages/<int:message_id>/choose/', views.choose_buyer, name='choose_buyer'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('payment/<int:item_id>/', views.process_payment, name='process_payment'),
    
    # Newly added URLs for the simulated payment workflow
    path('message/<int:message_id>/confirm_payment/', views.buyer_confirms_payment, name='confirm_payment'),
    #path('message/<int:message_id>/payment_confirmation/', views.payment_confirmation, name='payment_confirmation'),
    #path('verify_barcode/', views.verify_barcode, name='verify_barcode'),
    #path('barcode_verified/', views.barcode_verified, name='barcode_verified'),
    path('message/<int:message_id>/', views.message_detail, name='message_detail'),
    path('transaction/<str:transaction_id>/verify_pin/', views.enter_verification_pin, name='enter_verification_pin'),
    path('cancel_purchase/<int:item_id>/', views.cancel_purchase, name='cancel_purchase'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)