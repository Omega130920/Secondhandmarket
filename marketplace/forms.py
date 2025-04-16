from django import forms
from django.contrib.auth.models import User
from django import forms
from .models import Item, Category

class ItemForm(forms.ModelForm):
    category = forms.ModelChoiceField(queryset=Category.objects.all())
    image1 = forms.ImageField(required=False, label='Image 1 (Optional)')
    image2 = forms.ImageField(required=False, label='Image 2 (Optional)')
    image3 = forms.ImageField(required=False, label='Image 3 (Optional)')
    image4 = forms.ImageField(required=False, label='Image 4 (Optional)')
    image5 = forms.ImageField(required=False, label='Image 5 (Optional)')
    image6 = forms.ImageField(required=False, label='Image 6 (Optional)')

    class Meta:
        model = Item
        fields = ['title', 'description', 'category', 'condition', 'price', 'image1', 'image2', 'image3', 'image4', 'image5', 'image6']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'condition': forms.Select(),
        }

    def clean(self):
        cleaned_data = super().clean()
        image1 = self.files.get('image1')
        image2 = self.files.get('image2')
        image3 = self.files.get('image3')
        image4 = self.files.get('image4')
        image5 = self.files.get('image5')
        image6 = self.files.get('image6')

        uploaded_images = [img for img in [image1, image2, image3, image4, image5, image6] if img]

        if not uploaded_images:
            raise forms.ValidationError("At least one image is required.")
        if len(uploaded_images) > 6:
            raise forms.ValidationError("You can upload a maximum of 6 images.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            # The images are already saved to the Item model fields (image1 to image6)
        return instance

class UserRegistrationForm(forms.Form):
    first_name = forms.CharField(max_length=30, label='First Name')
    last_name = forms.CharField(max_length=30, label='Last Name')
    email = forms.EmailField(label='Email Address')
    cell_phone = forms.CharField(max_length=15, label='Cell Phone Number')
    id_document = forms.FileField(
        label='Upload ID Document (Word or PDF)',
        required=True,
        widget=forms.FileInput(attrs={'accept': '.doc,.docx,.pdf'})
    )
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

class PinVerificationForm(forms.Form):
    pin = forms.CharField(max_length=6, label='Enter PIN')

    def clean_password2(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords do not match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
    
class ContactSellerForm(forms.Form):
    subject = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'placeholder': 'Subject'}))
    body = forms.CharField(widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Your Message'}))
    
class VerificationPinForm(forms.Form):
    verification_pin = forms.CharField(max_length=6, label='Verification PIN')