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

An action is a button by default; `kind: "toggle"` with `checked` makes it a slide toggle in the toolbar and a
checkbox item in the menu (e.g. "Detailed View"). Controls that are not plain actions (a realm or node select) go
into the component's default content slot, at the start of the toolbar. Fixed-width content marked `tableActionsEnd`
(e.g. an info hint) goes after the buttons, as right-hand content that never folds into "More". Free text such as an
intro paragraph belongs on its own line outside the toolbar, or it pushes buttons into "More".

There are two ways to use it:

- A feature's `*-table-actions` component extends `TableActionsHost`, builds its `actions` as a
  `computed<TableAction[]>` and renders `<app-table-actions [actions]="actions()" />`. The table around it passes
  `featureActions.actionsMenu()` to the trigger. The token, container, container template, challenge, policy,
  user and resolver tables work this way:

  ```html
  <app-table-actions-trigger [menu]="userTableActions.actionsMenu()" />
  ```

- A page without such a component builds the `computed<TableAction[]>` itself and uses `app-table-actions`
  inline, with a template reference for the trigger. Permission checks go into each action's `visible`, and the
  trigger shows only while the menu holds an action. The template reference must be declared in the same template
  block as the trigger or in one that encloses it:

  ```html
  @if (pageActions.hasMenuActions()) {
    <app-table-actions-trigger [menu]="pageActions.menu()" />
  }
  ...
  <app-table-actions #pageActions [actions]="toolbarActions()" [collapseWhenEmpty]="true" />
  ```

  The realm, machine resolver, conditional access, API client, periodic task, event handler, locked user and
  blocklist tables and the external services tables (CA connectors, privacyIDEA servers, RADIUS servers, service
  IDs, SMS gateways, SMTP servers, token groups) work this way.

Some tables still hand-build their row. The authentication log's row is a filter bar rather than a set of actions
(a date-range picker, an inline slider, a custom menu), so it stays hand-built on purpose, like the token and
container tables' separate "More Filter" buttons. The user details token and container tables, the API client's
remembered devices and the self-service token and container tables have not been migrated yet.

Shared behaviour such as filtering, sorting and page sizes stays in `TableUtilsService`.

## Further help

To get more help on the Angular CLI use `ng help` or go check out
the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
