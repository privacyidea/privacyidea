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
import { ComponentRef } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ResolverService } from "@services/resolver/resolver.service";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { SqlResolverComponent } from "./sql-resolver.component";

describe("SqlResolverComponent", () => {
  let component: SqlResolverComponent;
  let componentRef: ComponentRef<SqlResolverComponent>;
  let fixture: ComponentFixture<SqlResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SqlResolverComponent, NoopAnimationsModule],
      providers: [{ provide: ResolverService, useClass: MockResolverService }]
    }).compileComponents();

    fixture = TestBed.createComponent(SqlResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should expose isValid and getValue", () => {
    expect(typeof component.isValid).toBe("function");
    expect(typeof component.getValue).toBe("function");
  });

  it("should update model when data input changes", () => {
    componentRef.setInput("data", {
      Driver: "mysql",
      Server: "localhost",
      Table: "users",
      Limit: 100,
      Map: "{}"
    });

    fixture.detectChanges();

    expect(component.model().Driver).toBe("mysql");
    expect(component.model().Server).toBe("localhost");
    expect(component.model().Table).toBe("users");
    expect(component.model().Limit).toBe("100");
    expect(component.model().Map).toBe("{}");
  });

  it("should parse boolean and numeric strings from data input", () => {
    componentRef.setInput("data", {
      Editable: "0",
      Port: "3306",
      poolSize: "10"
    });

    fixture.detectChanges();

    expect(component.model().Editable).toBe(false);
    expect(component.model().Port).toBe("3306");
    expect(component.model().poolSize).toBe("10");
  });

  it("should parse '1' and '0' strings as booleans from data input", () => {
    componentRef.setInput("data", {
      Editable: "1"
    });

    fixture.detectChanges();

    expect(component.model().Editable).toBe(true);
  });

  it("should apply SQL presets", () => {
    const preset = component.sqlPresets[0];
    component.applySqlPreset(preset);
    expect(component.model().Table).toBe(preset.table);
    expect(component.model().Map).toBe(preset.map);
    expect(component.model().poolSize).toBe("5");
    expect(component.model().poolTimeout).toBe("10");
    expect(component.model().poolRecycle).toBe("7200");
  });
});
