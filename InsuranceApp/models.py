from django.db import models

class Client(models.Model):
    full_name = models.CharField(max_length=255)
    birth_date = models.DateField()
    passport_number = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    class Meta:
        db_table = 'Clients'

    def __str__(self):
        return self.full_name

class Policy(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    policy_type = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    premium = models.FloatField()

    class Meta:
        db_table = 'Policies'

    def __str__(self):
        return f"{self.policy_type} ({self.client.full_name})"

class Claim(models.Model):
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE)
    claim_date = models.DateField()
    amount = models.FloatField()
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'Claims'

    def __str__(self):
        return f"Claim {self.id} ({self.policy.policy_type})"