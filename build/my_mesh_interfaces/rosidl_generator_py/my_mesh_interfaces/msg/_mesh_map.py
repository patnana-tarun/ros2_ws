# generated from rosidl_generator_py/resource/_idl.py.em
# with input from my_mesh_interfaces:msg/MeshMap.idl
# generated code does not contain a copyright notice

# This is being done at the module level and not on the instance level to avoid looking
# for the same variable multiple times on each instance. This variable is not supposed to
# change during runtime so it makes sense to only look for it once.
from os import getenv

ros_python_check_fields = getenv('ROS_PYTHON_CHECK_FIELDS', default='')


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_MeshMap(type):
    """Metaclass of message 'MeshMap'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('my_mesh_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'my_mesh_interfaces.msg.MeshMap')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__mesh_map
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__mesh_map
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__mesh_map
            cls._TYPE_SUPPORT = module.type_support_msg__msg__mesh_map
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__mesh_map

            from builtin_interfaces.msg import Time
            if Time.__class__._TYPE_SUPPORT is None:
                Time.__class__.__import_type_support__()

            from nav_msgs.msg import OccupancyGrid
            if OccupancyGrid.__class__._TYPE_SUPPORT is None:
                OccupancyGrid.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class MeshMap(metaclass=Metaclass_MeshMap):
    """Message class 'MeshMap'."""

    __slots__ = [
        '_session_id',
        '_sequence_id',
        '_transmission_stamp',
        '_map_data',
        '_check_fields',
    ]

    _fields_and_field_types = {
        'session_id': 'uint64',
        'sequence_id': 'uint64',
        'transmission_stamp': 'builtin_interfaces/Time',
        'map_data': 'nav_msgs/OccupancyGrid',
    }

    # This attribute is used to store an rosidl_parser.definition variable
    # related to the data type of each of the components the message.
    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('uint64'),  # noqa: E501
        rosidl_parser.definition.BasicType('uint64'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['builtin_interfaces', 'msg'], 'Time'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['nav_msgs', 'msg'], 'OccupancyGrid'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        if 'check_fields' in kwargs:
            self._check_fields = kwargs['check_fields']
        else:
            self._check_fields = ros_python_check_fields == '1'
        if self._check_fields:
            assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
                'Invalid arguments passed to constructor: %s' % \
                ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.session_id = kwargs.get('session_id', int())
        self.sequence_id = kwargs.get('sequence_id', int())
        from builtin_interfaces.msg import Time
        self.transmission_stamp = kwargs.get('transmission_stamp', Time())
        from nav_msgs.msg import OccupancyGrid
        self.map_data = kwargs.get('map_data', OccupancyGrid())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.get_fields_and_field_types().keys(), self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    if self._check_fields:
                        assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.session_id != other.session_id:
            return False
        if self.sequence_id != other.sequence_id:
            return False
        if self.transmission_stamp != other.transmission_stamp:
            return False
        if self.map_data != other.map_data:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def session_id(self):
        """Message field 'session_id'."""
        return self._session_id

    @session_id.setter
    def session_id(self, value):
        if self._check_fields:
            assert \
                isinstance(value, int), \
                "The 'session_id' field must be of type 'int'"
            assert value >= 0 and value < 18446744073709551616, \
                "The 'session_id' field must be an unsigned integer in [0, 18446744073709551615]"
        self._session_id = value

    @builtins.property
    def sequence_id(self):
        """Message field 'sequence_id'."""
        return self._sequence_id

    @sequence_id.setter
    def sequence_id(self, value):
        if self._check_fields:
            assert \
                isinstance(value, int), \
                "The 'sequence_id' field must be of type 'int'"
            assert value >= 0 and value < 18446744073709551616, \
                "The 'sequence_id' field must be an unsigned integer in [0, 18446744073709551615]"
        self._sequence_id = value

    @builtins.property
    def transmission_stamp(self):
        """Message field 'transmission_stamp'."""
        return self._transmission_stamp

    @transmission_stamp.setter
    def transmission_stamp(self, value):
        if self._check_fields:
            from builtin_interfaces.msg import Time
            assert \
                isinstance(value, Time), \
                "The 'transmission_stamp' field must be a sub message of type 'Time'"
        self._transmission_stamp = value

    @builtins.property
    def map_data(self):
        """Message field 'map_data'."""
        return self._map_data

    @map_data.setter
    def map_data(self, value):
        if self._check_fields:
            from nav_msgs.msg import OccupancyGrid
            assert \
                isinstance(value, OccupancyGrid), \
                "The 'map_data' field must be a sub message of type 'OccupancyGrid'"
        self._map_data = value
