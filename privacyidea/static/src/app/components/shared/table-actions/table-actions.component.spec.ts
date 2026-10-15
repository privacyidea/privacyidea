/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { Component, signal, viewChild } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatMenu, MatMenuModule } from "@angular/material/menu";
import { By } from "@angular/platform-browser";
import { TableAction, TableActionsComponent } from "./table-actions.component";
import { TableActionsHost } from "./table-actions-host";
import { TableActionsTriggerComponent } from "./table-actions-trigger.component";

@Component({
  imports: [TableActionsComponent, TableActionsTriggerComponent, MatMenuModule],
  template: `<app-table-actions
      [actions]="actions()"
      [collapseWhenEmpty]="collapseWhenEmpty()"
      [layout]="layout()"
      ><span class="end-hint" tableActionsEnd>Hint</span></app-table-actions
    >
    <app-table-actions-trigger [menu]="actionsMenu()" />
    <mat-menu #submenu="matMenu"><button mat-menu-item>Sub</button></mat-menu>
    <span class="has-menu-actions">{{ tableActionsComponent().hasMenuActions() }}</span>`
})
class HostComponent extends TableActionsHost {
  readonly actions = signal<TableAction[]>([]);
  readonly collapseWhenEmpty = signal(false);
  readonly layout = signal<"compact" | "roomy">("compact");
  readonly submenu = viewChild.required<MatMenu>("submenu");
  readonly tableActionsComponent = viewChild.required(TableActionsComponent);
}

@Component({
  imports: [TableActionsComponent, TableActionsTriggerComponent],
  template: `@if (pageActions.hasMenuActions()) {
      <app-table-actions-trigger [menu]="pageActions.menu()" />
    }
    <app-table-actions
      #pageActions
      [actions]="actions()"
      [collapseWhenEmpty]="true" />`
})
class InlineHostComponent {
  readonly actions = signal<TableAction[]>([]);
}

describe("TableActionsComponent", () => {
  let fixture: ComponentFixture<HostComponent>;
  let run: jest.Mock;

  const toolbarButtons = (): HTMLButtonElement[] =>
    Array.from(fixture.nativeElement.querySelectorAll("app-table-actions > div > button:not(.overflow-more-btn)"));

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    run = jest.fn();
  });

  function render(actions: TableAction[], collapseWhenEmpty = false): void {
    fixture = TestBed.createComponent(HostComponent);
    fixture.componentInstance.actions.set(actions);
    fixture.componentInstance.collapseWhenEmpty.set(collapseWhenEmpty);
    fixture.detectChanges();
  }

  const action = (overrides: Partial<TableAction>): TableAction => ({
    id: "a",
    label: "Action",
    tone: "primary",
    width: "m",
    icon: "folder",
    run,
    ...overrides
  });

  it("draws a button per visible action with the tone and width classes", () => {
    render([
      action({ id: "a" }),
      action({ id: "b", visible: false }),
      action({ id: "c", tone: "delete-secondary", width: "l" })
    ]);

    const buttons = toolbarButtons();
    expect(buttons).toHaveLength(2);
    expect(buttons[0].classList).toContain("action-button-primary");
    expect(buttons[0].classList).toContain("button-width-m");
    expect(buttons[1].classList).toContain("action-button-delete-secondary");
    expect(buttons[1].classList).toContain("button-width-l");
  });

  it("runs the action on click and honours disabled", () => {
    render([action({ id: "a" }), action({ id: "b", disabled: true })]);

    const [first, second] = toolbarButtons();
    first.click();
    expect(run).toHaveBeenCalledTimes(1);
    expect(second.disabled).toBe(true);
  });

  it("marks pinned actions for the overflow handling", () => {
    render([action({ id: "a", pinned: true }), action({ id: "b" })]);

    const [first, second] = toolbarButtons();
    expect(first.hasAttribute("data-overflow-pinned")).toBe(true);
    expect(second.hasAttribute("data-overflow-pinned")).toBe(false);
  });

  it("draws the badge only for actions that ask for it", () => {
    render([action({ id: "a", badge: true }), action({ id: "b" })]);

    const [first, second] = toolbarButtons();
    expect(first.querySelector(".icon-badge")).not.toBeNull();
    expect(second.querySelector(".icon-badge")).toBeNull();
  });

  it("makes only an action with a submenu a menu trigger", () => {
    render([action({ id: "a" })]);
    fixture.componentInstance.actions.set([
      action({ id: "a" }),
      action({ id: "b", submenu: fixture.componentInstance.submenu() })
    ]);
    fixture.detectChanges();

    const [plain, withMenu] = toolbarButtons();
    expect(plain.hasAttribute("aria-expanded")).toBe(false);
    expect(plain.classList).not.toContain("mat-mdc-menu-trigger");
    expect(withMenu.getAttribute("aria-expanded")).toBe("false");
    expect(withMenu.getAttribute("aria-haspopup")).toBe("menu");
  });

  it("keeps menu-only actions out of the toolbar", () => {
    render([action({ id: "a" }), action({ id: "b", placement: "menu" })]);

    expect(toolbarButtons()).toHaveLength(1);
  });

  it("draws an empty toolbar unless told to collapse", () => {
    render([action({ visible: false })]);
    expect(fixture.nativeElement.querySelector("app-table-actions > div")).not.toBeNull();

    fixture.componentInstance.collapseWhenEmpty.set(true);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector("app-table-actions > div")).toBeNull();
  });

  it("lists the visible actions in the menu behind the trigger", () => {
    render([action({ id: "a", label: "One" }), action({ id: "b", label: "Two", visible: false })]);

    fixture.debugElement.query(By.css(".table-actions-trigger")).nativeElement.click();
    fixture.detectChanges();

    const items = Array.from(document.querySelectorAll<HTMLElement>("[mat-menu-item]"));
    expect(items.map((item) => item.textContent?.trim())).toEqual(["folderOne"]);
    items[0].click();
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("draws the xl width tier", () => {
    render([action({ id: "a", width: "xl" })]);

    expect(toolbarButtons()[0].classList).toContain("button-width-xl");
  });

  it("draws a toggle action as a slide toggle after the spacer, before the end content", () => {
    render([action({ id: "a" }), action({ id: "t", kind: "toggle", checked: true, label: "Detailed" })]);

    expect(toolbarButtons()).toHaveLength(1);
    const row: HTMLElement = fixture.nativeElement.querySelector("app-table-actions > div");
    const children = Array.from(row.children);
    const spacer = row.querySelector(".spacer")!;
    const toggle = row.querySelector("mat-slide-toggle")!;
    const hint = row.querySelector(".end-hint")!;
    expect(children.indexOf(spacer)).toBeLessThan(children.indexOf(toggle));
    expect(children.indexOf(toggle)).toBeLessThan(children.indexOf(hint));
    expect(toggle.querySelector("button")!.getAttribute("aria-checked")).toBe("true");

    toggle.querySelector("button")!.click();
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("lists a toggle action in the menu as a checkbox item with its state", () => {
    render([action({ id: "t", kind: "toggle", checked: false, label: "Detailed" })]);

    fixture.debugElement.query(By.css(".table-actions-trigger")).nativeElement.click();
    fixture.detectChanges();

    const item = document.querySelector<HTMLElement>("[mat-menu-item]")!;
    expect(item.getAttribute("role")).toBe("menuitemcheckbox");
    expect(item.getAttribute("aria-checked")).toBe("false");
    expect(item.textContent).toContain("check_box_outline_blank");
    item.click();
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("disables a menu item that opens a submenu", () => {
    render([action({ id: "a" })]);
    fixture.componentInstance.actions.set([
      action({ id: "b", disabled: true, submenu: fixture.componentInstance.submenu() })
    ]);
    fixture.detectChanges();

    fixture.debugElement.query(By.css(".table-actions-trigger")).nativeElement.click();
    fixture.detectChanges();

    const item = document.querySelector<HTMLButtonElement>("[mat-menu-item]")!;
    expect(item.disabled).toBe(true);
  });

  it("tells whether the menu holds any action", () => {
    const flag = (): string => fixture.nativeElement.querySelector(".has-menu-actions").textContent.trim();
    render([action({ visible: false })]);
    expect(flag()).toBe("false");

    fixture.componentInstance.actions.set([action({ placement: "menu" })]);
    fixture.detectChanges();
    expect(flag()).toBe("true");
  });

  it("lets a trigger placed before it in the template follow hasMenuActions", async () => {
    const inline = TestBed.createComponent(InlineHostComponent);
    inline.componentInstance.actions.set([action({ id: "a" })]);
    inline.detectChanges();
    await inline.whenStable();
    expect(inline.nativeElement.querySelector(".table-actions-trigger")).not.toBeNull();

    inline.componentInstance.actions.set([action({ id: "a", visible: false })]);
    inline.detectChanges();
    await inline.whenStable();
    expect(inline.nativeElement.querySelector(".table-actions-trigger")).toBeNull();
  });
});
