from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from accounts.utils.validators import validate_image

class MyAccountManager(BaseUserManager):
    def create_user(self, first_name, last_name, username, email, password=None):
        if not email:
            raise ValueError('User must have an email address')
        if not username:
            raise ValueError('User must have a username')
        
        user = self.model(
            email=self.normalize_email(email),
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password):
        # For superusers, we supply empty strings for first_name and last_name,
        # since only email, username, and password are required.
        user = self.create_user(
            first_name='',
            last_name='',
            email=self.normalize_email(email),
            username=username,
            password=password,
        )
        user.is_admin = True
        user.is_active = True
        user.is_staff = True
        user.is_superadmin = True
        user.save(using=self._db)
        return user

class Account(AbstractBaseUser, PermissionsMixin):
    first_name    = models.CharField(max_length=50, blank=True)
    last_name     = models.CharField(max_length=50, blank=True)
    username      = models.CharField(max_length=50, unique=True)
    email         = models.EmailField(max_length=100, unique=True)
    phone_number  = models.CharField(max_length=50, blank=True)

    # Required fields
    date_joined   = models.DateTimeField(auto_now_add=True)
    last_login    = models.DateTimeField(auto_now_add=True)
    is_admin      = models.BooleanField(default=False)
    is_staff      = models.BooleanField(default=False)
    is_active     = models.BooleanField(default=False)
    is_superadmin = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # first_name and last_name are optional now

    objects = MyAccountManager()

    def full_name(self):
        # Strip extra spaces in case first_name or last_name is empty.
        return f'{self.first_name} {self.last_name}'.strip()

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True

class UserProfile(models.Model):
    user = models.OneToOneField(Account, on_delete=models.CASCADE)
    address_line_1 = models.CharField(blank=True, max_length=100)
    address_line_2 = models.CharField(blank=True, max_length=100)
    profile_picture = models.ImageField(blank=True, upload_to='userprofile', validators=[validate_image])
    city = models.CharField(blank=True, max_length=20)
    state = models.CharField(blank=True, max_length=20)
    country = models.CharField(blank=True, max_length=20)

    def __str__(self):
        # Return first_name if available; otherwise, fall back to email.
        return self.user.first_name if self.user.first_name else self.user.email

    def full_address(self):
        return f'{self.address_line_1} {self.address_line_2}'.strip()

class NewsletterSubscriber(models.Model):
    email = models.EmailField(max_length=100, unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email


class Admin2FA(models.Model):
    user = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='two_factor')
    totp_secret = models.CharField(max_length=64)
    is_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.email} 2FA'


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN_SUCCESS', 'Login Successful'),
        ('LOGIN_FAILED', 'Login Failed'),
        ('LOGOUT', 'Logout'),
        ('2FA_SUCCESS', '2FA Successful'),
        ('2FA_FAILED', '2FA Failed'),
        ('2FA_ENABLED', '2FA Enabled'),
        ('2FA_DISABLED', '2FA Disabled'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('ACCOUNT_CREATE', 'Account Created'),
        ('ACCOUNT_UPDATE', 'Account Updated'),
        ('ACCOUNT_DELETE', 'Account Deleted'),
        ('ADMIN_ACTION', 'Admin Action'),
        ('ADMIN_LOGIN_SUCCESS', 'Admin Login Successful'),
        ('ADMIN_LOGIN_FAILED', 'Admin Login Failed'),
        ('ADMIN_2FA_REQUIRED', 'Admin 2FA Required'),
        ('SENSITIVE_ACTION', 'Sensitive Action'),
    ]

    user = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    target_model = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f'{self.get_action_display()} - {self.user} @ {self.timestamp}'

