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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActivatedRoute, Router } from "@angular/router";
import { AuthService } from "@services/auth/auth.service";
import { UserData, UserService } from "@services/user/user.service";
import { MockUserService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { of } from "rxjs";
import { ROUTE_PATHS } from "@app/route_paths";
import { UserDetailsSelfServiceComponent } from "./user-details.self-service.component";

describe("UserDetailsSelfServiceComponent", () => {
  let component: UserDetailsSelfServiceComponent;
  let fixture: ComponentFixture<UserDetailsSelfServiceComponent>;
  let userServiceMock: MockUserService;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserDetailsSelfServiceComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { params: of({}) } },
        { provide: UserService, useClass: MockUserService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserDetailsSelfServiceComponent);
    userServiceMock = TestBed.inject(UserService) as unknown as MockUserService;
    router = TestBed.inject(Router);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("enrollNewToken navigates to token enrollment", () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.enrollNewToken();
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS_ENROLLMENT);
  });

  it("createNewContainer navigates to container create", () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.createNewContainer();
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.CONTAINERS_CREATE);
  });

  it("detailsEntries lists known keys in defined order, excluding 'editable'", () => {
    userServiceMock.user.set({
      username: "alice",
      givenname: "Alice",
      surname: "Smith",
      email: "alice@example.com",
      phone: "",
      mobile: "",
      description: "desc",
      userid: "u1",
      resolver: "res1",
      editable: true
    });

    const entries = component.detailsEntries();
    const keys = entries.map((e) => e.key);

    expect(keys).toEqual([
      "username",
      "givenname",
      "surname",
      "description",
      "email",
      "phone",
      "mobile",
      "userid",
      "resolver"
    ]);
    expect(keys).not.toContain("editable");
  });

  it("detailsEntries normalizes null/empty values to '-'", () => {
    userServiceMock.user.set({
      username: "alice",
      givenname: null,
      surname: "  ",
      email: "",
      resolver: "res1"
    } as unknown as UserData);

    const map = new Map(component.detailsEntries().map((e) => [e.key, e.value]));
    expect(map.get("givenname")).toBe("-");
    expect(map.get("surname")).toBe("-");
    expect(map.get("email")).toBe("-");
    expect(map.get("username")).toBe("alice");
    expect(map.get("resolver")).toBe("res1");
  });

  it("detailsEntries appends unknown extra keys after the predefined order", () => {
    userServiceMock.user.set({
      username: "alice",
      resolver: "res1",
      foo: "bar",
      editable: false
    } as unknown as UserData);

    const keys = component.detailsEntries().map((e) => e.key);
    expect(keys[0]).toBe("username");
    expect(keys).toContain("foo");
    expect(keys).not.toContain("editable");
  });

  it("uses the localized label when available, falls back to the key otherwise", () => {
    userServiceMock.user.set({ username: "alice", foo: "bar" } as unknown as UserData);
    const entries = component.detailsEntries();
    const usernameEntry = entries.find((e) => e.key === "username");
    const fooEntry = entries.find((e) => e.key === "foo");
    expect(usernameEntry?.label).toBe(component.labels["username"]);
    expect(fooEntry?.label).toBe("foo");
  });

  it("normalizes undefined values to '-' and preserves array values as-is", () => {
    userServiceMock.user.set({
      username: "alice",
      givenname: undefined,
      email: ["a@example.com", "b@example.com"]
    } as unknown as UserData);

    const map = new Map(component.detailsEntries().map((e) => [e.key, e.value]));
    expect(map.get("givenname")).toBe("-");
    expect(Array.isArray(map.get("email"))).toBe(true);
    expect((map.get("email") as string[]).length).toBe(2);
  });

  it("returns no entries when user data is empty/null", () => {
    userServiceMock.user.set(null as unknown as UserData);
    expect(component.detailsEntries()).toEqual([]);
  });

  it("exposes labels for every key in detailOrder", () => {
    for (const key of component.detailOrder) {
      expect(component.labels[key]).toBeTruthy();
    }
  });

  it("excludedKeys contains 'editable'", () => {
    expect(component.excludedKeys.has("editable")).toBe(true);
  });

  it("renders header and one label/value cell per entry in the template", () => {
    userServiceMock.user.set({
      username: "alice",
      email: "a@example.com"
    } as unknown as UserData);
    fixture.detectChanges();

    const host: HTMLElement = fixture.nativeElement;
    expect(host.querySelector(".details-header h3")?.textContent).toContain("Your Details");
    const labels = host.querySelectorAll(".detail-field-label");
    const values = host.querySelectorAll(".detail-field-value");
    expect(labels.length).toBe(component.detailsEntries().length);
    expect(values.length).toBe(component.detailsEntries().length);
    expect(host.textContent).toContain("alice");
    expect(host.textContent).toContain("a@example.com");
  });

  it("renders array values collapsed by default and expands on toggle", () => {
    userServiceMock.user.set({
      username: "alice",
      email: ["a@example.com", "b@example.com"]
    } as unknown as UserData);
    fixture.detectChanges();

    const host: HTMLElement = fixture.nativeElement;
    const ul = host.querySelector(".detail-field-value ul");
    expect(ul).toBeTruthy();
    expect(ul!.querySelectorAll("li").length).toBe(1);

    const toggle = host.querySelector(".value-toggle") as HTMLButtonElement;
    expect(toggle).toBeTruthy();
    expect(toggle.getAttribute("aria-expanded")).toBe("false");

    toggle.click();
    fixture.detectChanges();

    expect(host.querySelector(".detail-field-value ul")!.querySelectorAll("li").length).toBe(2);
    expect(host.querySelector(".value-toggle")!.getAttribute("aria-expanded")).toBe("true");
  });
});
