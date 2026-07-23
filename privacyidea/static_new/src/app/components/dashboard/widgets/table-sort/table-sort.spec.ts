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
import { Component, computed, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { TableSortHeaderComponent } from "./table-sort-header.component";
import { TableSort } from "./table-sort";

interface Row {
  name: string;
  value: number | null;
}

const createSort = (): TableSort<Row, "name" | "value"> =>
  new TableSort<Row, "name" | "value">({
    name: (row) => row.name,
    value: (row) => row.value
  });

describe("TableSort", () => {
  const rows: Row[] = [
    { name: "beta", value: 2 },
    { name: "alpha", value: null },
    { name: "gamma", value: 10 }
  ];

  it("keeps the original order until a column is activated", () => {
    expect(createSort().apply(rows)).toEqual(rows);
  });

  it("sorts strings ascending and descending", () => {
    const sort = createSort();

    sort.toggle("name");
    expect(sort.apply(rows).map((row) => row.name)).toEqual(["alpha", "beta", "gamma"]);

    sort.toggle("name");
    expect(sort.apply(rows).map((row) => row.name)).toEqual(["gamma", "beta", "alpha"]);
  });

  it("sorts numbers numerically and keeps missing values last", () => {
    const sort = createSort();

    sort.toggle("value");
    expect(sort.apply(rows).map((row) => row.value)).toEqual([2, 10, null]);

    sort.toggle("value");
    expect(sort.apply(rows).map((row) => row.value)).toEqual([10, 2, null]);
  });

  it("returns to the default order on the third toggle", () => {
    const sort = createSort();

    sort.toggle("name");
    sort.toggle("name");
    sort.toggle("name");

    expect(sort.active()).toBeNull();
    expect(sort.direction()).toBe("asc");
    expect(sort.apply(rows)).toEqual(rows);
  });

  it("restarts ascending when another column is activated", () => {
    const sort = createSort();

    sort.toggle("name");
    sort.toggle("name");
    sort.toggle("value");

    expect(sort.active()).toBe("value");
    expect(sort.direction()).toBe("asc");
  });

  it("does not modify the source array", () => {
    const source = [...rows];
    const sort = createSort();
    sort.toggle("name");

    sort.apply(source);

    expect(source).toEqual(rows);
  });
});

@Component({
  standalone: true,
  imports: [TableSortHeaderComponent],
  template: `
    <table>
      <thead>
        <tr>
          <th>
            <app-table-sort-header key="name" [sortState]="sort" label="Name" />
          </th>
          <th>
            <app-table-sort-header key="value" [sortState]="sort" label="Value" />
          </th>
        </tr>
      </thead>
      <tbody>
        @for (row of sortedRows(); track row.name) {
          <tr>
            <td>{{ row.name }}</td>
          </tr>
        }
      </tbody>
    </table>
  `
})
class HostComponent {
  readonly sort = createSort();
  readonly rows = signal<Row[]>([
    { name: "beta", value: 2 },
    { name: "alpha", value: null }
  ]);
  readonly sortedRows = computed(() => this.sort.apply(this.rows()));
}

describe("TableSortHeaderComponent", () => {
  let fixture: ComponentFixture<HostComponent>;

  const buttons = (): HTMLButtonElement[] => Array.from(fixture.nativeElement.querySelectorAll("button.sort-button"));
  const icons = (): string[] =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-icon")).map((icon) =>
      (icon as HTMLElement).textContent?.trim()
    );
  const names = (): string[] =>
    Array.from(fixture.nativeElement.querySelectorAll("td")).map((cell) => (cell as HTMLElement).textContent?.trim());

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  it("renders the label and the neutral icon while unsorted", () => {
    expect(fixture.nativeElement.querySelector("th")?.textContent).toContain("Name");
    expect(icons()).toEqual(["unfold_more", "unfold_more"]);
    expect(names()).toEqual(["beta", "alpha"]);
  });

  it("sorts the rows on click and reflects the direction in the icon", () => {
    buttons()[0].click();
    fixture.detectChanges();

    expect(icons()[0]).toBe("keyboard_arrow_upward");
    expect(names()).toEqual(["alpha", "beta"]);

    buttons()[0].click();
    fixture.detectChanges();

    expect(icons()[0]).toBe("keyboard_arrow_downward");
    expect(names()).toEqual(["beta", "alpha"]);
  });

  it("returns to the neutral icon on the third click", () => {
    buttons()[0].click();
    buttons()[0].click();
    buttons()[0].click();
    fixture.detectChanges();

    expect(icons()[0]).toBe("unfold_more");
    expect(names()).toEqual(["beta", "alpha"]);
  });

  it("resets the previous column when another one is activated", () => {
    buttons()[0].click();
    fixture.detectChanges();

    buttons()[1].click();
    fixture.detectChanges();

    expect(icons()).toEqual(["unfold_more", "keyboard_arrow_upward"]);
  });
});
