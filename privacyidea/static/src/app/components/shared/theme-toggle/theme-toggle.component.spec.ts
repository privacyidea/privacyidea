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
import { provideZonelessChangeDetection, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ThemeService } from "@services/theme/theme.service";
import { ThemeToggleComponent } from "./theme-toggle.component";

describe("ThemeToggleComponent", () => {
  let fixture: ComponentFixture<ThemeToggleComponent>;
  let component: ThemeToggleComponent;
  let themeService: { visualTheme: ReturnType<typeof signal<"light" | "dark">>; setTheme: jest.Mock };

  const host = (): HTMLElement => fixture.nativeElement;

  const input = (): HTMLInputElement =>
    host().querySelector<HTMLInputElement>(".theme-toggle input") as HTMLInputElement;

  beforeEach(async () => {
    themeService = { visualTheme: signal<"light" | "dark">("light"), setTheme: jest.fn() };

    await TestBed.configureTestingModule({
      imports: [ThemeToggleComponent],
      providers: [provideZonelessChangeDetection(), { provide: ThemeService, useValue: themeService }]
    }).compileComponents();

    fixture = TestBed.createComponent(ThemeToggleComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should show the light icon and read as unchecked in light mode", () => {
    expect(input().checked).toBe(false);
    expect(host().textContent).toContain("light_mode");
  });

  it("should press in and show the dark icon once dark mode is in effect", () => {
    themeService.visualTheme.set("dark");
    fixture.detectChanges();

    expect(input().checked).toBe(true);
    expect(host().textContent).toContain("dark_mode");
  });

  it("should switch to dark from light", () => {
    input().dispatchEvent(new Event("change"));

    expect(themeService.setTheme).toHaveBeenCalledWith("dark");
  });

  it("should switch to light from dark", () => {
    themeService.visualTheme.set("dark");
    fixture.detectChanges();

    input().dispatchEvent(new Event("change"));

    expect(themeService.setTheme).toHaveBeenCalledWith("light");
  });

  it("should label itself with the mode it switches to", () => {
    expect(input().getAttribute("aria-label")).toBe("Switch to dark mode");

    themeService.visualTheme.set("dark");
    fixture.detectChanges();

    expect(input().getAttribute("aria-label")).toBe("Switch to light mode");
  });
});
