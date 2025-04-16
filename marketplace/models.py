from django.db import models
from django.contrib.auth.models import User
from PIL import Image # type: ignore
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Additional fields for the user profile
    display_name = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    id_document = models.ImageField(upload_to='id_documents/', null=True, blank=True)

    # New address fields
    region = models.CharField(max_length=100, blank=True)
    suburb = models.CharField(max_length=100, blank=True)
    street_address = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.user.username

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class Item(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    condition = models.CharField(
        max_length=50,
        choices=[
            ('new', 'New'),
            ('like_new', 'Like New'),
            ('very_good', 'Very Good'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('damaged', 'Damaged'),
        ],
        default='good'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image1 = models.ImageField(upload_to='item_images/', null=True, blank=True)
    image2 = models.ImageField(upload_to='item_images/', null=True, blank=True)
    image3 = models.ImageField(upload_to='item_images/', null=True, blank=True)
    image4 = models.ImageField(upload_to='item_images/', null=True, blank=True)
    image5 = models.ImageField(upload_to='item_images/', null=True, blank=True)
    image6 = models.ImageField(upload_to='item_images/', null=True, blank=True)
    image1_thumbnail = models.ImageField(upload_to='item_thumbnails/', blank=True, null=True)
    image2_thumbnail = models.ImageField(upload_to='item_thumbnails/', blank=True, null=True)
    image3_thumbnail = models.ImageField(upload_to='item_thumbnails/', blank=True, null=True)
    image4_thumbnail = models.ImageField(upload_to='item_thumbnails/', blank=True, null=True)
    image5_thumbnail = models.ImageField(upload_to='item_thumbnails/', blank=True, null=True)
    image6_thumbnail = models.ImageField(upload_to='item_thumbnails/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for img_field in ['image1', 'image2', 'image3', 'image4', 'image5', 'image6']:
            img = getattr(self, img_field)
            thumb_field = f'{img_field}_thumbnail'
            if img:
                self.create_thumbnail(img, getattr(self, thumb_field), (300, 300)) # Adjust size as needed

    def create_thumbnail(self, image_field, thumb_field_name, size):
        img = Image.open(image_field)
        img = img.convert('RGB')
        img.thumbnail(size)

        thumb_io = BytesIO()
        img.save(thumb_io, 'JPEG', quality=80)

        thumb_file = InMemoryUploadedFile(
            thumb_io,
            None,
            image_field.name,
            'image/jpeg',
            thumb_io.tell(),
            None
        )
        setattr(self, thumb_field_name, thumb_file)
        return thumb_file  # Return the created thumbnail file

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for img_field_name in ['image1', 'image2', 'image3', 'image4', 'image5', 'image6']:
            img = getattr(self, img_field_name)
            thumb_field_name = f'{img_field_name}_thumbnail'
            if img:
                thumbnail = self.create_thumbnail(img, thumb_field_name, (300, 300))
                # No need to explicitly save here, as the super().save() at the beginning
                # and the subsequent save() at the end will handle it.
        super().save(*args, **kwargs) # Save again after creating thumbnails

from django.contrib.auth.models import User

class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    item = models.ForeignKey('Item', on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_accepted = models.BooleanField(default=False)  # Seller accepted buyer's offer
    payment_processed = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True) # Unique transaction identifier
    # Removed: verification_barcode
    # Removed: barcode_scanned
    # Removed: funds_released

    def __str__(self):
        return f"Message from {self.sender.username} to {self.recipient.username} regarding {self.item.title}"

    class Meta:
        ordering = ['-sent_at']

from django.contrib.auth.models import User

class Notification(models.Model):
    recipient = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    message = models.ForeignKey('Message', on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(max_length=255)  # e.g., 'buyer_chosen', 'message_received'
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.notification_type}"

    class Meta:
        ordering = ['-created_at']
        
class ItemTransaction(models.Model):
    item = models.ForeignKey(to='Item', on_delete=models.CASCADE)
    buyer = models.ForeignKey(to=User, related_name='purchases', on_delete=models.CASCADE)
    seller = models.ForeignKey(to=User, related_name='sales', on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=255, unique=True)
    payment_timestamp = models.DateTimeField(default=timezone.now)
    verification_pin = models.CharField(max_length=6)
    pin_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Transaction ID: {self.transaction_id} for {self.item.title}"