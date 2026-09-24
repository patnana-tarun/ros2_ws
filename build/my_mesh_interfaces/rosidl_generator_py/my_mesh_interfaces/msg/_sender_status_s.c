// generated from rosidl_generator_py/resource/_idl_support.c.em
// with input from my_mesh_interfaces:msg/SenderStatus.idl
// generated code does not contain a copyright notice
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <Python.h>
#include <stdbool.h>
#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-function"
#endif
#include "numpy/ndarrayobject.h"
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif
#include "rosidl_runtime_c/visibility_control.h"
#include "my_mesh_interfaces/msg/detail/sender_status__struct.h"
#include "my_mesh_interfaces/msg/detail/sender_status__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool my_mesh_interfaces__msg__sender_status__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[51];
    {
      char * class_name = NULL;
      char * module_name = NULL;
      {
        PyObject * class_attr = PyObject_GetAttrString(_pymsg, "__class__");
        if (class_attr) {
          PyObject * name_attr = PyObject_GetAttrString(class_attr, "__name__");
          if (name_attr) {
            class_name = (char *)PyUnicode_1BYTE_DATA(name_attr);
            Py_DECREF(name_attr);
          }
          PyObject * module_attr = PyObject_GetAttrString(class_attr, "__module__");
          if (module_attr) {
            module_name = (char *)PyUnicode_1BYTE_DATA(module_attr);
            Py_DECREF(module_attr);
          }
          Py_DECREF(class_attr);
        }
      }
      if (!class_name || !module_name) {
        return false;
      }
      snprintf(full_classname_dest, sizeof(full_classname_dest), "%s.%s", module_name, class_name);
    }
    assert(strncmp("my_mesh_interfaces.msg._sender_status.SenderStatus", full_classname_dest, 50) == 0);
  }
  my_mesh_interfaces__msg__SenderStatus * ros_message = _ros_message;
  {  // session_id
    PyObject * field = PyObject_GetAttrString(_pymsg, "session_id");
    if (!field) {
      return false;
    }
    assert(PyLong_Check(field));
    ros_message->session_id = PyLong_AsUnsignedLongLong(field);
    Py_DECREF(field);
  }
  {  // last_sequence_sent
    PyObject * field = PyObject_GetAttrString(_pymsg, "last_sequence_sent");
    if (!field) {
      return false;
    }
    assert(PyLong_Check(field));
    ros_message->last_sequence_sent = PyLong_AsUnsignedLongLong(field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * my_mesh_interfaces__msg__sender_status__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of SenderStatus */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("my_mesh_interfaces.msg._sender_status");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "SenderStatus");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  my_mesh_interfaces__msg__SenderStatus * ros_message = (my_mesh_interfaces__msg__SenderStatus *)raw_ros_message;
  {  // session_id
    PyObject * field = NULL;
    field = PyLong_FromUnsignedLongLong(ros_message->session_id);
    {
      int rc = PyObject_SetAttrString(_pymessage, "session_id", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // last_sequence_sent
    PyObject * field = NULL;
    field = PyLong_FromUnsignedLongLong(ros_message->last_sequence_sent);
    {
      int rc = PyObject_SetAttrString(_pymessage, "last_sequence_sent", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }

  // ownership of _pymessage is transferred to the caller
  return _pymessage;
}
