import os
import json
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from annotation.models import DataSet, Exercise, Tier
import annotation.utils


class Command(BaseCommand):
    """
    Upload sounds from a directory
    """

    help = 'Upload sounds from a given directory'

    @staticmethod
    def add_arguments(parser):
        parser.add_argument('path', type=str, default=False, help='path to dataset')

        parser.add_argument('description', type=str, default=False, help='description file')

        parser.add_argument('dataset', type=str, default=False, help='data set name')

    def handle(self, *args, **options):
        dataset_path = options['path']
        dataset_name = options['dataset']

        # check if data set exists
        try:
            data_set = DataSet.objects.get(name=dataset_name)
        except ObjectDoesNotExist:
            print("This data set doesn't exist in the web, please provide an existing one or create it")
            return 0
        description_file_path = os.path.join(dataset_path, options['description'])
        descriptions = json.load(open(description_file_path))
        for exercise_name, exercise_description in descriptions.items():
            # create exercise if it doesn't exist
            try:
                exercise = Exercise.objects.get(name=exercise_name)
            except ObjectDoesNotExist:
                exercise = Exercise.objects.create(name=exercise_name, data_set=data_set)
                annotation.utils.create_exercise_directory(dataset_name, exercise_name)
                # check if there is a rubric file to create the tiers and labels
                rubric_file_path = os.path.join(dataset_path, 'rubric.json')
                if os.path.exists(rubric_file_path):
                    rubric_data = json.load(open(rubric_file_path))
                    for tier_name, tier_data in rubric_data.items():
                        try:
                            Tier.objects.get(name=tier_name, exercise=exercise)
                        except ObjectDoesNotExist:
                            if 'parent_tier' in tier_data:
                                try:
                                    parent_tier = Tier.objects.get(name=tier_data['parent_tier'], exercise=exercise)
                                except ObjectDoesNotExist:
                                    parent_tier = Tier.objects.create(name=tier_data['parent_tier'], exercise=exercise)
                                tier = Tier.objects.create(name=tier_name, exercise=exercise, parent_tier=parent_tier)
                            else:
                                tier = Tier.objects.create(name=tier_name, exercise=exercise)
                            if tier_name.find('Overall') != -1 or tier_name.find('entire') != -1:
                                tier.entire_sound = True
                                tier.save()
                            print("Created tier %s in exercise %s" % (tier.name, exercise.name))
                else:
                    # create initial tier "whole sound"
                    Tier.objects.create(name="entire sound", exercise=exercise, entire_sound=True)

            # create reference sound
            try:
                reference_sound_file_relative_path = exercise_description['ref_media']
                source_path = os.path.join(dataset_path, reference_sound_file_relative_path)
                reference_sound_filename = os.path.basename(reference_sound_file_relative_path)

                # copy the sound into media
                annotation.utils.copy_sound_into_media(source_path, dataset_name, exercise_name,
                                                       reference_sound_filename)

                reference_sound = annotation.utils.get_or_create_sound_object(exercise, reference_sound_filename,
                                                                              source_path)
                exercise.reference_sound = reference_sound
                exercise.save()
                print("Created sound reference for exercise %s" % exercise_name)
                # check if there is a file for the annotations of the reference sound
                reference_sound_annotations_file_path = os.path.splitext(source_path)[0] + '.trans_json'
                if os.path.exists(reference_sound_annotations_file_path):
                    annotation.utils.create_annotations(reference_sound_annotations_file_path, reference_sound)
            except KeyError:
                print("The exercise %s does not have reference sound" % exercise_name)

            # create pitch reference file
            try:
                reference_pitch_file_relative_path = exercise_description['tanpura']
                source_path = os.path.join(dataset_path, reference_pitch_file_relative_path)
                reference_pitch_filename = os.path.basename(reference_pitch_file_relative_path)
                # copy the file into media
                destination_path = annotation.utils.copy_sound_into_media(source_path, dataset_name, exercise_name,
                                                                          reference_pitch_filename)
                exercise.reference_pitch_sound.name = destination_path
                exercise.save()
                print("Created pitch reference for exercise %s" % exercise_name)
            except KeyError:
                print("The exercise %s does not have a pitch reference")

            for sound_description in exercise_description['recs']:
                try:
                    sound_file_relative_path = sound_description['path']
                    source_path = os.path.join(dataset_path, sound_file_relative_path)
                    sound_filename = os.path.basename(sound_file_relative_path)

                    # copy the sound into media
                    annotation.utils.copy_sound_into_media(source_path, dataset_name, exercise_name, sound_filename)

                    sound = annotation.utils.get_or_create_sound_object(exercise, sound_filename, source_path)

                    print("Created sound %s:%s of exercise %s" % (sound.id, sound_filename, exercise_name))
                except Exception as e:
                    print(e.message)


