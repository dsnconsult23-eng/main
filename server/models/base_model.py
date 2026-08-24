# soap-web-services/server/models/base_model.py
from pydantic import BaseModel as PydanticBaseModel, Field
from lxml import etree
import logging
from typing import TypeVar, Type, Optional, Any, Dict, List

logger = logging.getLogger(__name__)
T = TypeVar('T', bound='BaseXmlModel')

def get_field_alias(model_cls: Type[PydanticBaseModel], field_name: str, for_serialization: bool) -> str:
    """Helper to get the alias for a field, preferring serialization/validation alias."""
    field_info = model_cls.model_fields.get(field_name)
    if not field_info:
        return field_name

    alias = None
    if for_serialization:
        if field_info.serialization_alias:
            alias = field_info.serialization_alias
        elif field_info.alias:
            alias = field_info.alias
    else: # For validation (parsing from XML)
        if field_info.validation_alias:
            alias = field_info.validation_alias
        elif field_info.alias:
            alias = field_info.alias
            
    return alias if alias else field_name


class BaseXmlModel(PydanticBaseModel):
    def to_xml_element(self, root_tag_name_override: Optional[str] = None) -> etree._Element:
        """
        Converts the Pydantic model to an lxml etree._Element.
        Respects serialization_alias or alias for XML tag names.
        """
        model_class_name = self.__class__.__name__
        root_tag_name = root_tag_name_override if root_tag_name_override else model_class_name
        root_el = etree.Element(root_tag_name)

        for field_name, value in self.model_dump(exclude_none=True, by_alias=False).items():
            if value is None:
                continue

            xml_tag_name = get_field_alias(self.__class__, field_name, for_serialization=True)

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, BaseXmlModel):
                        list_item_element = item.to_xml_element(root_tag_name_override=xml_tag_name)
                        root_el.append(list_item_element)
                    elif item is not None:  # Skip None values in lists
                        etree.SubElement(root_el, xml_tag_name).text = str(item)
            elif isinstance(value, BaseXmlModel):
                nested_element = value.to_xml_element(root_tag_name_override=xml_tag_name)
                root_el.append(nested_element)
            else:
                etree.SubElement(root_el, xml_tag_name).text = str(value)
        return root_el

    @classmethod
    def from_xml_element(cls: Type[T], xml_element: etree._Element) -> T:
        """
        Creates a Pydantic model instance from an lxml etree._Element.
        Respects validation_alias or alias for XML tag names.
        """
        data: Dict[str, Any] = {}
        class_name = cls.__name__

        for field_py_name, field_info in cls.model_fields.items():
            xml_tag_name = get_field_alias(cls, field_py_name, for_serialization=False)
            
            is_list = hasattr(field_info.annotation, '__origin__') and field_info.annotation.__origin__ in (list, List)
            list_item_type_actual = None
            if is_list and hasattr(field_info.annotation, '__args__') and field_info.annotation.__args__:
                list_item_type_actual = field_info.annotation.__args__[0]

            found_elements = xml_element.findall(xml_tag_name)

            if found_elements:
                if is_list:
                    data[field_py_name] = []
                    for el in found_elements:
                        if list_item_type_actual and issubclass(list_item_type_actual, BaseXmlModel):
                            try:
                                data[field_py_name].append(list_item_type_actual.from_xml_element(el))
                            except ValueError as e_item:
                                logger.error(f"Error parsing list item <{xml_tag_name}> for {class_name}.{field_py_name}: {e_item}")
                                raise ValueError(f"Error in list item <{xml_tag_name}> for {field_py_name}: {e_item}") from e_item
                        elif el.text is not None:
                            data[field_py_name].append(el.text)
                        # Skip empty elements in lists
                elif len(found_elements) == 1:
                    el = found_elements[0]
                    field_type_actual = field_info.annotation
                    if field_type_actual and issubclass(field_type_actual, BaseXmlModel):
                        try:
                            data[field_py_name] = field_type_actual.from_xml_element(el)
                        except ValueError as e_nested:
                            logger.error(f"Error parsing nested model <{xml_tag_name}> for {class_name}.{field_py_name}: {e_nested}")
                            raise ValueError(f"Error in nested model <{xml_tag_name}> for {field_py_name}: {e_nested}") from e_nested
                    elif el.text is not None:
                        data[field_py_name] = el.text
                    elif not list(el) and el.text is None:  # Empty tag
                        data[field_py_name] = None
                else:
                    logger.warning(f"Multiple elements ({len(found_elements)}) found for non-list field '{field_py_name}'. Using the first one.")
                    el = found_elements[0]
                    if el.text is not None: 
                        data[field_py_name] = el.text
            elif is_list:
                # Initialize empty list if no elements found for list field
                data[field_py_name] = []

        try:
            instance = cls(**data)
            return instance
        except Exception as e_pydantic:
            logger.error(f"Pydantic validation error creating {class_name} from XML element <{xml_element.tag}>: {e_pydantic}. Processed data: {data}", exc_info=True)
            raise ValueError(f"Pydantic validation error for {class_name} (XML: <{xml_element.tag}>): {e_pydantic}") from e_pydantic

    class Config:
        populate_by_name = True