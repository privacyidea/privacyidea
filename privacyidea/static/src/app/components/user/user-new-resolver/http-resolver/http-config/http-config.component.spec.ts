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
import { MatCheckbox } from "@angular/material/checkbox";
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { HttpConfigComponent, HttpConfigModel } from "./http-config.component";

const initialModel: HttpConfigModel = {
  method: "GET",
  endpoint: "/users",
  headers: "",
  requestMapping: "",
  responseMapping: "",
  hasSpecialErrorHandler: false,
  errorResponse: ""
};

@Component({
  selector: "app-http-config-host",
  imports: [HttpConfigComponent],
  template: `
    <app-http-config
      [description]="description()"
      [endpointHint]="endpointHint()"
      [field]="configForm"
      title="Config" />
  `
})
class HostComponent {
  model = signal<HttpConfigModel>({ ...initialModel });
  configForm = form(this.model);
  description = signal<string | undefined>(undefined);
  endpointHint = signal<string | undefined>(undefined);
}

describe("HttpConfigComponent", () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HostComponent;

  const input = (placeholder: string) =>
    fixture.debugElement.query(By.css(`[placeholder='${placeholder}']`)).nativeElement as
      HTMLInputElement | HTMLTextAreaElement;

  const type = (element: HTMLInputElement | HTMLTextAreaElement, value: string) => {
    element.value = value;
    element.dispatchEvent(new Event("input"));
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("shows the values of the field", () => {
    expect((input("/users") as HTMLInputElement).value).toBe("/users");
    expect(fixture.debugElement.query(By.directive(MatSelect)).componentInstance.value).toBe("GET");
    expect(host.configForm().dirty()).toBe(false);
  });

  it("writes typed text into the model and marks the form dirty", () => {
    type(input("/users"), "/people");
    type(input('{"Content-Type":"application/json; charset=UTF-8"}'), '{"a":"b"}');
    type(input('{"customerid":"{userid}","accessKey":"{secre3t!}"}'), '{"id":"{userid}"}');
    type(input('{"Authorization":"Bearer {access_token}"}'), '{"token":"{access_token}"}');

    expect(host.model()).toEqual(
      expect.objectContaining({
        endpoint: "/people",
        headers: '{"a":"b"}',
        requestMapping: '{"id":"{userid}"}',
        responseMapping: '{"token":"{access_token}"}'
      })
    );
    expect(host.configForm().dirty()).toBe(true);
  });

  it("marks the form dirty when only the method changes", () => {
    const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
    select.open();
    fixture.detectChanges();
    const options = document.querySelectorAll<HTMLElement>("mat-option");
    Array.from(options)
      .find((option) => option.textContent?.trim() === "PUT")!
      .click();
    fixture.detectChanges();

    expect(host.model().method).toBe("PUT");
    expect(host.configForm().dirty()).toBe(true);
  });

  it("marks the form dirty when only Special Error Handling changes and shows the response field", () => {
    expect(
      fixture.debugElement.query(By.css('[placeholder=\'{"success": false, "message": "An error occurred!"}\']'))
    ).toBeNull();

    const checkbox = fixture.debugElement.query(By.directive(MatCheckbox));
    checkbox.query(By.css("input")).nativeElement.click();
    fixture.detectChanges();

    expect(host.model().hasSpecialErrorHandler).toBe(true);
    expect(host.configForm().dirty()).toBe(true);
    type(input('{"success": false, "message": "An error occurred!"}'), '{"success": false}');
    expect(host.model().errorResponse).toBe('{"success": false}');
  });

  it("clears the endpoint with the clear button and marks the form dirty", () => {
    fixture.debugElement.query(By.css("app-clear-button button")).nativeElement.click();
    fixture.detectChanges();

    expect(host.model().endpoint).toBe("");
    expect(host.configForm().dirty()).toBe(true);
    expect(fixture.debugElement.query(By.css("app-clear-button"))).toBeNull();
  });

  it("renders the description and the endpoint hint only when given", () => {
    expect(fixture.nativeElement.querySelector(".auth-description")).toBeNull();
    expect(fixture.nativeElement.querySelector("mat-hint")).toBeNull();

    host.description.set("Describes the request.");
    host.endpointHint.set("Possible tags: {userid}");
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector(".auth-description").textContent).toContain("Describes the request.");
    expect(fixture.nativeElement.querySelectorAll("mat-hint").length).toBe(2);
    expect(fixture.nativeElement.querySelector("mat-hint").textContent).toContain("Possible tags: {userid}");
  });
});
