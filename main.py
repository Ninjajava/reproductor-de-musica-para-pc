"""Punto de entrada de JULIOPRODDJ."""
from djapp.controller import DJController
from djapp.view import DJView


def main() -> None:
    vista = DJView()
    controlador = DJController(vista)
    vista.set_controller(controlador)
    vista.mainloop()


if __name__ == "__main__":
    main()
