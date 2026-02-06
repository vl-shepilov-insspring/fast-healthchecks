# Usage

How you mount health checks depends on the framework:

- **FastAPI:** Use `HealthcheckRouter` with one or more `Probe` instances and pass it to `app.include_router()`.
- **FastStream:** Use the `health()` function from `fast_healthchecks.integrations.faststream` with your probes and options; it returns the routes to register with the app.
- **Litestar:** Use the `health()` function from `fast_healthchecks.integrations.litestar` with your probes and options; it returns the routes to register with the app.

Create the health check endpoint dynamically using different conditions.
Each condition is a callable, and you can even have dependencies inside it:

=== "examples/probes.py"

    ```python
    {%
        include-markdown "../examples/probes.py"
    %}
    ```

=== "FastAPI"

    ```python
    {%
        include-markdown "../examples/fastapi_example/main.py"
    %}
    ```

=== "FastStream"

    ```python
    {%
        include-markdown "../examples/faststream_example/main.py"
    %}
    ```

=== "Litestar"

    ```python
    {%
        include-markdown "../examples/litestar_example/main.py"
    %}
    ```

You can find examples for each framework here:

- [FastAPI example](https://github.com/shepilov-vladislav/fast-healthchecks/tree/main/examples/fastapi_example)
- [FastStream example](https://github.com/shepilov-vladislav/fast-healthchecks/tree/main/examples/faststream_example)
- [Litestar example](https://github.com/shepilov-vladislav/fast-healthchecks/tree/main/examples/litestar_example)
