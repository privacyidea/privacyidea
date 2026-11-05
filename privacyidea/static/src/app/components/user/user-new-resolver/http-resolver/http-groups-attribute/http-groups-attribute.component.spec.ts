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
import { form } from "@angular/forms/signals";
import { MatSelect } from "@angular/material/select";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { By } from "@angular/platform-browser";
import { HttpGroupsAttributeComponent, UserGroupsModel, userGroupsRules } from "./http-groups-attribute.component";

const initialModel: UserGroupsModel = {
  active: false,
  pi_user_groups_key: "groups",
  user_groups_attribute: "",
  method: "GET",
  endpoint: ""
};

@Component({
  selector: "app-http-groups-attribute-host",
  imports: [HttpGroupsAttributeComponent],
  template: `<app-http-groups-attribute
    [field]="groupsForm"
    [resolverType]="resolverType()" />`
})
class HostComponent {
  model = signal<UserGroupsModel>({ ...initialModel });
  groupsForm = form(this.model, (f) => userGroupsRules(f));
  resolverType = signal("default");
}

describe("HttpGroupsAttributeComponent", () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HostComponent;

  const inputs = () =>
    fixture.debugElement.queryAll(By.css("input[matInput]")).map((e) => e.nativeElement as HTMLInputElement);

  const toggle = () => fixture.debugElement.query(By.directive(MatSlideToggle));

  const activate = () => {
    toggle().query(By.css("button")).nativeElement.click();
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(fixture.debugElement.query(By.directive(HttpGroupsAttributeComponent))).toBeTruthy();
  });

  it("disables the groups fields while the retrieval is inactive", () => {
    expect(host.groupsForm.pi_user_groups_key().disabled()).toBe(true);
    expect(host.groupsForm.user_groups_attribute().disabled()).toBe(true);
    expect(host.groupsForm.method().disabled()).toBe(true);
    expect(host.groupsForm.endpoint().disabled()).toBe(true);
    expect(inputs().every((input) => input.disabled)).toBe(true);
    expect(fixture.debugElement.query(By.directive(MatSelect)).componentInstance.disabled).toBe(true);
  });

  it("enables the groups fields and marks the form dirty when the toggle is switched on", () => {
    activate();

    expect(host.model().active).toBe(true);
    expect(host.groupsForm().dirty()).toBe(true);
    expect(host.groupsForm.pi_user_groups_key().disabled()).toBe(false);
    expect(inputs().every((input) => !input.disabled)).toBe(true);
    expect(fixture.debugElement.query(By.directive(MatSelect)).componentInstance.disabled).toBe(false);
  });

  it("writes typed text into the model", () => {
    activate();
    const [key, attribute, endpoint] = inputs();
    key.value = "members";
    key.dispatchEvent(new Event("input"));
    attribute.value = "name";
    attribute.dispatchEvent(new Event("input"));
    endpoint.value = "/users/{userid}/groups";
    endpoint.dispatchEvent(new Event("input"));

    expect(host.model()).toEqual(
      expect.objectContaining({
        pi_user_groups_key: "members",
        user_groups_attribute: "name",
        endpoint: "/users/{userid}/groups"
      })
    );
  });

  it("marks the form dirty when only the method changes", () => {
    host.model.update((m) => ({ ...m, active: true }));
    fixture.detectChanges();
    expect(host.groupsForm().dirty()).toBe(false);

    fixture.debugElement.query(By.directive(MatSelect)).componentInstance.open();
    fixture.detectChanges();
    Array.from(document.querySelectorAll<HTMLElement>("mat-option"))
      .find((option) => option.textContent?.trim() === "PATCH")!
      .click();
    fixture.detectChanges();

    expect(host.model().method).toBe("PATCH");
    expect(host.groupsForm().dirty()).toBe(true);
  });

  it("shows the tooltip of the active state", () => {
    const tooltip = () =>
      fixture.debugElement
        .query(By.directive(HttpGroupsAttributeComponent))
        .componentInstance.slideToggleTooltipSignal();
    expect(tooltip()).toContain("Enable");

    activate();
    expect(tooltip()).toContain("Disable");
  });

  it("shows the Entra ID labels and no method and endpoint fields", () => {
    host.resolverType.set("entraidresolver");
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain("Group Identifier");
    expect(fixture.debugElement.query(By.directive(MatSelect))).toBeNull();
    expect(inputs().length).toBe(2);
  });

  it("lists the realm tag of the endpoint for Keycloak", () => {
    expect(fixture.nativeElement.textContent).not.toContain("{realm}");

    host.resolverType.set("keycloakresolver");
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain("{realm}");
  });
});
