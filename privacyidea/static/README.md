# Webui

This project was generated with [Angular CLI](https://github.com/angular/angular-cli) version 18.2.8.

## Setup the development environment

You need [Node.js](https://nodejs.org/en/download) which comes bundled with the node package manager (npm).

In `privacyidea/static/` run `npm install` to install all the pinned dependencies.
If the Angular CLI is not installed globally it can be executed with `npm run-script ng ...` from the `static/`
directory.

## Development server

Run `ng serve` for a dev server. Navigate to `http://localhost:4200/`. The application will automatically reload if you
change any of the source files.

To change the privacyIDEA server to connect to, edit the `target` entry in `static/src/proxy.conf.json`.

## Code scaffolding

Run `ng generate component component-name` to generate a new component. You can also use
`ng generate directive|pipe|service|class|guard|interface|enum|module`.

## Build

Run `ng build` to build the project. The build artifacts will be stored in the `dist/` directory.

## Running unit tests

Run `ng test` to execute the unit tests via [Karma](https://karma-runner.github.io).

## Running end-to-end tests

Run `ng e2e` to execute the end-to-end tests via a platform of your choice. To use this command, you need to first add a
package that implements end-to-end testing capabilities.

## Table actions

A table's action buttons (create, delete, copy, ...) are described once as a `TableAction[]` and drawn by
`app-table-actions` (`src/app/components/shared/table-actions`). It renders the toolbar of buttons above the
table, which folds into a "More" menu when it does not fit, and the equivalent `mat-menu` that opens from the
compact `app-table-actions-trigger` next to the filter once the table is scrolled. The table-specific part is the
action list; the layout, button styling and overflow handling live in the shared component.

A feature's `*-table-actions` component extends `TableActionsHost`, builds its `actions` as a `computed<TableAction[]>`
and renders `<app-table-actions [actions]="actions()" />`. Controls that are not plain actions (a realm select) go
into the component's content. The table around it passes `featureActions.actionsMenu()` to the trigger:

```html
<app-table-actions-trigger [menu]="userTableActions.actionsMenu()" />
```

Shared behaviour such as filtering, sorting and page sizes stays in `TableUtilsService`.

## Further help

To get more help on the Angular CLI use `ng help` or go check out
the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
