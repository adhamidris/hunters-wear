from django.db import models, transaction

# Create your models here.



class Products(models.Model):

    classifications = [
        ('tshirts', 'T Shirts'),
        ('shorts', 'Shorts'),
        ('best-sellers', 'Best Seller'),
        ('suit', 'Suit'),
        ('trouser', 'Trouser'),
    ]


    name = models.CharField(max_length=30, null=True, blank=True)
    price = models.IntegerField(null=True, blank=True)
    compare_price = models.IntegerField(null=True, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    classification = models.CharField(choices=classifications, max_length=12)
    best_seller = models.BooleanField(default=False, null=True, blank=True)

    def __str__(self):
        return f"{self.classification} - {self.name} - {self.price}"
    

class ProductSize(models.Model):
    SIZE_CHOICES = [
        ('XS', 'XSmall'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'XLarge'),
        ('XXL', 'XXLarge'),
        ('30', '30'),
        ('32', '32'),
        ('33', '33'),
        ('34', '34'),
        ('36', '36'),
        ('38', '38'),
        ('40', '40'),
        ('42', '42'),
        ('44', '44'),
        ('46', '46'),
    ]

    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='productsizes')
    size = models.CharField(max_length=12, choices=SIZE_CHOICES)
    stock_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ['product', 'size']

    def __str__(self):
        return f"{self.product.name} - {self.get_size_display()} ({self.stock_count} in stock)"
    
    @property
    def is_in_stock(self):
        return self.stock_count > 0

class Order(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    first_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    area = models.CharField(max_length=50)
    nearest_landmark = models.CharField(max_length=100)

    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.IntegerField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            with transaction.atomic():
                last = Order.objects.select_for_update().order_by('-id').first()
                last_num = int(last.order_number) if (last and str(last.order_number).isdigit()) else 0
                self.order_number = str(last_num + 1)
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    size = models.CharField(max_length=3, blank=True, null=True, choices=[  # ADD this line
        ('XS', 'XS'),
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ])
    quantity = models.PositiveIntegerField(default=1)
    price = models.IntegerField()

    def __str__(self):
        size_text = f" ({self.get_size_display()})" if self.size else ""
        return f"{self.quantity} x {self.product}{size_text}"
    
    @property
    def total_price(self):
        return self.quantity * self.price
    