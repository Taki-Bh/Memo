from dataclasses import dataclass

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QObject,
)
from PySide6.QtWidgets import QWidget


@dataclass
class TweenInfo:
    """
    Configuration for a tween animation.

    duration:
        Animation duration in milliseconds.

    easing_style:
        Qt easing curve, e.g.
        QEasingCurve.Type.OutCubic

    easing_direction:
        Optional easing direction.

        Most Qt easing curves already encode their direction
        (OutCubic, InQuad, InOutCubic, etc.), so this is mainly
        provided for convenience.
    """

    duration: int = 1000
    easing_style: QEasingCurve.Type = QEasingCurve.Type.Linear


class TweenService:
    """
    Roblox-like tween service for PySide6.

    Example:

        info = TweenInfo(
            duration=1000,
            easing_style=QEasingCurve.Type.OutCubic,
        )

        TweenService.create(
            widget,
            b"pos",
            start_position,
            target_position,
            info,
        )
    """

    @staticmethod
    def create(
        widget: QWidget,
        property_name: bytes,
        start_value,
        end_value,
        tween_info: TweenInfo,
    ) -> QPropertyAnimation:
        """
        Create and start a tween.

        Args:
            widget:
                QWidget whose property will be animated.

            property_name:
                Qt property to animate.

                Examples:
                    b"pos"
                    b"size"
                    b"geometry"
                    b"maximumHeight"
                    b"minimumWidth"

            start_value:
                Initial value of the property.

            end_value:
                Final value of the property.

            tween_info:
                TweenInfo containing duration/easing.

        Returns:
            The running QPropertyAnimation.
        """

        animation = QPropertyAnimation(widget, property_name)

        animation.setDuration(tween_info.duration)
        animation.setStartValue(start_value)
        animation.setEndValue(end_value)
        animation.setEasingCurve(tween_info.easing_style)

        # Keep the animation alive for the duration of the tween.
        widget._tween_animation = animation

        animation.start()

        return animation

    @staticmethod
    def cancel(widget: QWidget):
        """
        Stop the currently running tween on a widget.
        """

        animation = getattr(widget, "_tween_animation", None)

        if animation is not None:
            animation.stop()
            widget._tween_animation = None

    @staticmethod
    def is_playing(widget: QWidget) -> bool:
        """
        Check whether a widget currently has a running tween.
        """

        animation = getattr(widget, "_tween_animation", None)

        if animation is None:
            return False

        return animation.state() == QPropertyAnimation.State.Running