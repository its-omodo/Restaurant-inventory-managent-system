from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0001_initial"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="saletransaction",
            name="sales_salet_source_2adbd7_idx",
        ),
        migrations.RemoveField(
            model_name="saletransaction",
            name="source",
        ),
        migrations.RemoveField(
            model_name="saletransaction",
            name="terminal_id",
        ),
        migrations.RemoveField(
            model_name="saletransaction",
            name="payment_method",
        ),
        migrations.DeleteModel(
            name="POSIntegration",
        ),
    ]
