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
import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { TableAction, TableActionsComponent } from "./table-actions.component";
import { TableActionsHost } from "./table-actions-host";
import { TableActionsTriggerComponent } from "./table-actions-trigger.component";

@Component({
  imports: [TableActionsComponent, TableActionsTriggerComponent],
  template: `<app-table-actions
      [actions]="actions()"
      [collapseWhenEmpty]="collapseWhenEmpty()"
      [layout]="layout()" />
    <app-table-actions-trigger [menu]="actionsMenu()" />`
})
class HostComponent extends TableActionsHost {
  readonly actions = signal<TableAction[]>([]);
  readonly collapseWhenEmpty = signal(false);
  readonly layout = signal<"compact" | "roomy">("compact");
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
});
