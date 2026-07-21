from django.db import migrations


def create_policy_pages(apps, schema_editor):
    PolicyPage = apps.get_model('pages', 'PolicyPage')

    PolicyPage.objects.get_or_create(
        page_type='privacy',
        defaults={
            'title': 'Privacy Policy',
            'meta_description': 'Privacy Policy for LuckyTech Innovation Ground - how we collect, use, and protect your data.',
            'content': '''
<h2>1. Information We Collect</h2>
<p>We collect information you provide directly to us, including:</p>
<ul>
<li>Name, email address, and phone number when you create an account or place an order</li>
<li>Payment information processed securely through our payment partners</li>
<li>Communication data when you contact our support team</li>
<li>Device and browser information for security and analytics purposes</li>
</ul>

<h2>2. How We Use Your Information</h2>
<p>We use the information we collect to:</p>
<ul>
<li>Process and fulfil your orders</li>
<li>Send order updates and important account notifications</li>
<li>Improve our website, products, and services</li>
<li>Detect and prevent fraud or unauthorised access</li>
<li>Comply with legal obligations</li>
</ul>

<h2>3. Data Protection</h2>
<p>We implement industry-standard security measures to protect your personal information. All data is encrypted in transit using TLS and stored securely on protected servers.</p>

<h2>4. Third-Party Sharing</h2>
<p>We do not sell your personal information. We may share data with trusted service providers who assist in operating our website and conducting business, provided they agree to keep this information confidential.</p>

<h2>5. Cookies</h2>
<p>We use cookies to enhance your browsing experience, analyse site traffic, and personalise content. You can control cookie preferences through your browser settings.</p>

<h2>6. Your Rights</h2>
<p>You have the right to access, correct, or delete your personal data. To exercise these rights, please contact us at <strong>info@lig.com.gh</strong>.</p>

<h2>7. Contact Us</h2>
<p>For questions about this Privacy Policy, contact us at:</p>
<ul>
<li>Email: info@lig.com.gh</li>
<li>Phone: +233 59 188 4422</li>
<li>Address: Adweso-Koforidua Road, Eastern Region, Ghana</li>
</ul>
''',
        },
    )

    PolicyPage.objects.get_or_create(
        page_type='terms',
        defaults={
            'title': 'Terms of Service',
            'meta_description': 'Terms of Service for LuckyTech Innovation Ground - rules governing the use of our website and services.',
            'content': '''
<h2>1. Acceptance of Terms</h2>
<p>By accessing or using the LuckyTech Innovation Ground website and services, you agree to be bound by these Terms of Service. If you do not agree, please do not use our services.</p>

<h2>2. Products and Services</h2>
<p>All product descriptions, images, and specifications are provided as accurately as possible. However, we reserve the right to modify prices, availability, and product details without prior notice.</p>

<h2>3. Orders and Payment</h2>
<p>By placing an order, you are making an offer to purchase. We reserve the right to accept or decline any order. Payment must be completed before order processing begins. We accept payments via Paystack and Hubtel.</p>

<h2>4. Shipping and Delivery</h2>
<p>Delivery timelines are estimates and not guaranteed. LiG is not liable for delays caused by shipping carriers or unforeseen circumstances. Risk of loss transfers to you upon delivery.</p>

<h2>5. Returns and Refunds</h2>
<p>Products may be returned within 7 days of delivery if they are defective or not as described. Refunds are processed to the original payment method within 5-10 business days of approved returns.</p>

<h2>6. Warranty</h2>
<p>Products are covered by manufacturer warranty unless otherwise stated. Extended warranty options may be available for select products at the time of purchase.</p>

<h2>7. Intellectual Property</h2>
<p>All content on this website, including text, graphics, logos, and software, is the property of LuckyTech Innovation Ground and protected by copyright laws.</p>

<h2>8. Limitation of Liability</h2>
<p>LiG shall not be liable for any indirect, incidental, or consequential damages arising from the use of our products or services. Our total liability shall not exceed the purchase price of the product.</p>

<h2>9. Governing Law</h2>
<p>These terms are governed by the laws of the Republic of Ghana. Any disputes shall be resolved in the courts of Ghana.</p>

<h2>10. Contact</h2>
<p>For questions about these Terms, contact us at <strong>info@lig.com.gh</strong> or call +233 59 188 4422.</p>
''',
        },
    )

    PolicyPage.objects.get_or_create(
        page_type='cookies',
        defaults={
            'title': 'Cookie Policy',
            'meta_description': 'Cookie Policy for LuckyTech Innovation Ground - how we use cookies on our website.',
            'content': '''
<h2>1. What Are Cookies</h2>
<p>Cookies are small text files stored on your device when you visit our website. They help us provide you with a better experience by remembering your preferences and analysing how our site is used.</p>

<h2>2. Types of Cookies We Use</h2>

<h3>Essential Cookies</h3>
<p>These are necessary for the website to function properly. They enable core features like shopping cart functionality, secure checkout, and account authentication.</p>

<h3>Analytics Cookies</h3>
<p>We use analytics cookies to understand how visitors interact with our website. This helps us improve site performance and user experience. We use Google Analytics for this purpose.</p>

<h3>Functional Cookies</h3>
<p>These cookies remember your preferences such as language settings, currency, and recently viewed products to provide a personalised experience.</p>

<h3>Marketing Cookies</h3>
<p>Marketing cookies are used to deliver relevant advertisements and track the effectiveness of our marketing campaigns across platforms.</p>

<h2>3. Managing Cookies</h2>
<p>You can control and manage cookies through your browser settings. Most browsers allow you to:</p>
<ul>
<li>View what cookies are stored and delete them individually</li>
<li>Block third-party cookies</li>
<li>Block cookies from particular sites</li>
<li>Block all cookies</li>
<li>Delete all cookies when you close your browser</li>
</ul>

<h2>4. Impact of Disabling Cookies</h2>
<p>Disabling certain cookies may affect the functionality of our website. Essential cookies cannot be disabled as they are required for the site to work correctly.</p>

<h2>5. Updates to This Policy</h2>
<p>We may update this Cookie Policy from time to time. Changes will be posted on this page with an updated revision date.</p>

<h2>6. Contact Us</h2>
<p>If you have questions about our use of cookies, please contact us at <strong>info@lig.com.gh</strong>.</p>
''',
        },
    )


def reverse_func(apps, schema_editor):
    PolicyPage = apps.get_model('pages', 'PolicyPage')
    PolicyPage.objects.filter(page_type__in=['privacy', 'terms', 'cookies']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0002_policypage"),
    ]

    operations = [
        migrations.RunPython(create_policy_pages, reverse_func),
    ]
