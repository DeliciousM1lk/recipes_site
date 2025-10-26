from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Recipe, Step

@receiver(post_delete, sender=Recipe)
def delete_recipe_image(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)

@receiver(post_delete, sender=Step)
def delete_step_image(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
