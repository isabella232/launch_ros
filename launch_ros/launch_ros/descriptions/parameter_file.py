# Copyright 2020 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module for a description of a ParameterFile."""

import io
import os
from pathlib import Path
from typing import Optional
from typing import Text

from launch import Substitution
from launch import SomeSubstitutionsType_types_tuple
from launch import SomeSubstitutionsType
from launch.frontend import parse_if_substitutions
from launch.utilities import ensure_argument_type
from launch.utilities import normalize_to_list_of_substitutions
from launch.utilities import perform_substitutions
from launch.utilities import type_utils
from launch.utilities.typing_file_path import FilePath


class ParameterFile:
    """Describes a ROS parameter file."""

    def __init__(
        self,
        param_file: Union[FilePath, SomeSubstitutionsType],
        *,
        allow_substs: bool = False
    ) -> None:
        """
        Construct a parameter file description.

        :param param_file: Either a path to a parameter file, or the contents of the file.
        :param allow_subst: Allow substitutions in the parameter file.
        """
        ensure_argument_type(
            param_file,
            SomeSubstitutionsType_types_tuple + (os.PathLike, bytes),
            'param_file',
            'ParameterFile()'
        )
        ensure_argument_type(
            allow_substs,
            bool,
            'allow_subst',
            'ParameterFile()'
        )
        self.__param_file: Union[List[Substitution], FilePath] = param_file
        if isinstance(param_file, SomeSubstitutionsType_types_tuple):
            self.__param_file = normalize_to_list_of_substitutions(param_file)
        self.__allow_substs = allow_substs
        self.__evaluated_param_file: Optional[Path] = None
        self.__created_tmp_file = False

    @property
    def param_file(self) -> Union[FilePath, SomeSubstitutionsType]:
        """Getter for parameter file."""
        if self.__evaluated_parameter_file is not None:
            return self.__evaluated_parameter_file
        return self.__param_file

    @property
    def allow_substs(self) -> bool:
        """Getter for parameter value type."""
        return self.__allow_substs

    def __str__(self) -> Text:
        return (
            'launch_ros.description.ParameterFile'
            f'(param_file={self.param_file}, allow_substs={self.allow_substs})'
        )

    def evaluate(self, context: LaunchContext) -> Path:
        """Evaluate and return a parameter file path."""
        if self.__evaluated_param_file is not None:
            return self.__evaluated_param_file

        param_file = self.__param_file
        if isinstance(param_file, list):
            # list of substitutions
            param_file = perform_substitutions(context, self.__param_file)
        param_file_path: Path = Path(param_file)
        if self.__allow_substs:
            with (
                open(param_file_path, 'r') as f,
                NamedTemporaryFile(mode='w', prefix='launch_params_', delete=False) as h
            ):
                read = yaml.safe_load(f)
                new_yaml_dict = {}
                for node, node_dict in read:
                    node = __perform_substitutions(context, node)
                    new_content = {}
                    for section, param_dict in node_dict:
                        if section == 'ros__parameters':
                            param_dict = {
                                __perform_substitutions(context, k): __perform_substitutions(context, v)
                                for k, v in param_dict
                            }
                        new_content[section] = param_dict
                    new_yaml_dict[node] = new_content
                yaml.dump(new_yaml_dict, h, default_flow_style=False)
                param_file_path = Path(h.name)
                self.__created_tmp_file = True
        self.__evaluated_param_file = param_file_path
        return param_file_path

    def clean_up(self):
        if self.__evaluated_param_file is not None and self.__created_tmp_file:
            os.unlink(self.__evaluated_param_file)


def __perform_substitutions(context, value):
    parsed_value = parse_if_substitutions(value)
    normalized_value = type_utils.normalize_typed_substitution(parsed_value, None)
    return type_utils.perform_typed_substitution(context, normalized_value, None)