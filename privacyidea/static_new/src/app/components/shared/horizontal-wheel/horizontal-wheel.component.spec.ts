import { ComponentFixture, TestBed, fakeAsync, tick } from "@angular/core/testing";
import { HorizontalWheelComponent } from "./horizontal-wheel.component";
import { CommonModule } from "@angular/common";
import { Component, ViewChild, signal } from "@angular/core";

@Component({
  template: `<app-horizontal-wheel
    [values]="values"
    (onSelect)="onSelect($event)"></app-horizontal-wheel>`,
  standalone: true,
  imports: [CommonModule, HorizontalWheelComponent]
})
class TestHostComponent {
  values = signal(["A", "B", "C"]);
  selected: string | null = null;
  onSelect(val: string) {
    this.selected = val;
  }
  @ViewChild(HorizontalWheelComponent) wheel!: HorizontalWheelComponent;
}

describe("HorizontalWheelComponent", () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let host: TestHostComponent;
  let component: HorizontalWheelComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestHostComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    host = fixture.componentInstance;
    fixture.detectChanges();
    component = host.wheel;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should handle mouse move when dragging", () => {
    component.isDragging = true;
    (component as any).containerElement = { scrollLeft: 50, offsetWidth: 200, style: {} };
    component.startX = 100;
    component.scrollLeft = 50;
    const fakeEvent = { preventDefault: () => {}, pageX: 120 } as any as MouseEvent;

    component.onMouseMove(fakeEvent);

    expect((component as any).containerElement.scrollLeft).toBe(30);
  });
});
