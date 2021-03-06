import os
import json
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from annotation.models import DataSet, Exercise, Tier, Tag, Annotation, User
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

        parser.add_argument('user', type=str, default=False, help='user name to create the annotations')

        parser.add_argument('force_annotations', type=bool, nargs='?', default=False,
                            help='force re-upload annotations')
        parser.add_argument('--create_segments', type=str, default=False,
                            help='create segments for all sounds with specific start/end times')

    @staticmethod
    def create_tiers(tiers_data, exercise):
        for tier_name, tier_data in tiers_data.items():
            point_annotations = False
            if 'point_annotations' in tier_data:
                point_annotations = True
            try:
                tier = Tier.objects.get(name=tier_name, exercise=exercise)
            except ObjectDoesNotExist:
                if 'parent_tier' in tier_data or 'special_parent_tier' in tier_data:
                    tier = Tier.objects.create(name=tier_name, exercise=exercise, point_annotations=point_annotations)
                    if 'parent_tier' in tier_data:
                        try:
                            parent_tier = Tier.objects.get(name=tier_data['parent_tier'], exercise=exercise)
                        except ObjectDoesNotExist:
                            parent_tier = Tier.objects.create(name=tier_data['parent_tier'], exercise=exercise,
                                                              point_annotations=point_annotations)
                        tier.parent_tier = parent_tier
                    if 'special_parent_tier' in tier_data:
                        try:
                            special_parent_tier = Tier.objects.get(name=tier_data['special_parent_tier'],
                                                                   exercise=exercise)
                        except ObjectDoesNotExist:
                            special_parent_tier = Tier.objects.create(name=tier_data['special_parent_tier'],
                                                                      exercise=exercise,
                                                                      point_annotations=point_annotations)
                        tier.special_parent_tier = special_parent_tier
                    tier.save()
                else:
                    tier = Tier.objects.create(name=tier_name, exercise=exercise, point_annotations=point_annotations)
                if tier_name.find('Overall') != -1 or tier_name.find('entire') != -1:
                    tier.entire_sound = True
                if 'similarity_dimensions' in tier_data:
                    tier.similarity_keys = tier_data['similarity_dimensions']
                tier.save()
                print("Created tier %s in exercise %s" % (tier.name, exercise.name))
            # CREATE TAGS IF DEFINED IN THE RUBRIC FILE
            if 'rubric' in tier_data:
                for tag_data in tier_data['rubric']['ratings']:
                    tag, created = Tag.objects.get_or_create(name=tag_data)
                    if created:
                        print("Created tag: %s" % tag.name)
                    if tier not in tag.tiers.all():
                        tag.tiers.add(tier)

    def handle(self, *args, **options):
        dataset_path = options['path']
        dataset_name = options['dataset']
        username = options['user']

        data_set, _ = DataSet.objects.get_or_create(name=dataset_name)
        try:
            user = User.objects.get(username=username)
        except ObjectDoesNotExist:
            print("This user doesn't exist in the database, please sing up or provide an existing username")
            return 0
        data_set.users.add(user)
        data_set.save()

        description_file_path = os.path.join(dataset_path, options['description'])
        descriptions = json.load(open(description_file_path))
        for exercise_id, exercise_description in descriptions.items():
            exercise_name = exercise_description['name']

            # CREATE EXERCISE

            try:
                exercise = Exercise.objects.get(exercise_id=exercise_id, data_set=data_set)
            except ObjectDoesNotExist:
                exercise = Exercise.objects.create(name=exercise_name, data_set=data_set, exercise_id=exercise_id)
                annotation.utils.create_exercise_directory(dataset_name, exercise_name)

            # CREATE TIERS
            # check if there is a rubric file to create the tiers and labels

            # # Riyaz tier creation definition
            rubric_file_path = os.path.join(dataset_path, 'rubric.json')
            if os.path.exists(rubric_file_path):
                rubric_data = json.load(open(rubric_file_path))
                self.create_tiers(rubric_data, exercise)
            else:
                # create initial tier "whole sound"
                Tier.objects.create(name="entire sound", exercise=exercise, entire_sound=True)

            # CREATE REFERENCE PITCH

            try:
                reference_pitch_file_relative_path = exercise_description['tanpura']
                source_path = os.path.join(dataset_path, reference_pitch_file_relative_path)
                reference_pitch_filename = os.path.basename(reference_pitch_file_relative_path)
                # copy the file into media
                destination_path = annotation.utils.copy_sound_into_media(source_path, dataset_name, exercise_name,
                                                                          reference_pitch_filename)
                exercise.reference_pitch_sound.name = destination_path
                exercise.save()
            except KeyError:
                print("The exercise %s does not have a pitch reference")

            # CREATE REFERENCE SOUND

            try:
                reference_sound_file_relative_path = exercise_description['ref_media']
                source_path = os.path.join(dataset_path, reference_sound_file_relative_path)
                reference_sound_filename = os.path.basename(reference_sound_file_relative_path)

                # copy the sound into media
                reference_sound_filename = annotation.utils.copy_sound_into_media(source_path, dataset_name,
                                                                                  exercise_name,
                                                                                  reference_sound_filename)
                name = "%s %s" % (exercise.name, 'reference')
                reference_sound = annotation.utils.get_or_create_sound_object(exercise, reference_sound_filename,
                                                                              source_path, name=name)
                exercise.reference_sound = reference_sound
                exercise.save()

                # CREATE REFERENCE ANNOTATIONS

                reference_sound_annotations_file_path = os.path.splitext(source_path)[0] + '.trans_json'
                if os.path.exists(reference_sound_annotations_file_path):
                    if options['force_annotations']:
                        reference_sound.annotations.all().delete()
                    if not reference_sound.annotations.all():
                        annotation.utils.create_annotations(reference_sound_annotations_file_path, reference_sound,
                                                            username, True)
                # Create annotations for reference sound according to parameter
                if options['create_segments']:
                    start_time, end_time = [int(i) for i in str(options['create_segments'])]
                    for tier in exercise.tiers.all():
                        Annotation.objects.create(name="",
                                                  start_time=start_time,
                                                  end_time=end_time, sound=reference_sound, tier=tier,
                                                  user=user)
            except KeyError:
                print("The exercise %s does not have reference sound" % exercise_name)

            # CREATE SOUNDS

            for sound_description in exercise_description['recs']:
                try:
                    sound_file_relative_path = sound_description['path']
                    source_path = os.path.join(dataset_path, sound_file_relative_path)
                    sound_filename = os.path.basename(sound_file_relative_path)

                    # copy the sound into media
                    sound_filename = annotation.utils.copy_sound_into_media(source_path, dataset_name, exercise_name,
                                                                            sound_filename)
                    name = None
                    if '_id' in sound_description:
                        name = sound_description['_id']
                    sound = annotation.utils.get_or_create_sound_object(exercise, sound_filename, source_path,
                                                                        name=name)

                    # CREATE ANNOTATIONS

                    sound_annotations_file_path = os.path.splitext(source_path)[0] + '.json'
                    if os.path.exists(sound_annotations_file_path):
                        if options['force_annotations']:
                            sound.annotations.all().delete()
                        if not sound.annotations.all():
                            annotation.utils.create_annotations(sound_annotations_file_path, sound, username, False)

                    # Create annotations for each sound according to parameter
                    if options['create_segments']:
                        start_time, end_time = [int(i) for i in str(options['create_segments'])]
                        user = User.objects.get(username=username)
                        for tier in exercise.tiers.all():
                            Annotation.objects.create(name="",
                                                      start_time=start_time,
                                                      end_time=end_time, sound=sound, tier=tier,
                                                      user=user)
                except Exception as e:
                    print("Error while creating sounds and annotations from files: %s" % e)

