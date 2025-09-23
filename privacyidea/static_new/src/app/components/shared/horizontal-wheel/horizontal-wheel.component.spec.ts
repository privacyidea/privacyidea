import { ComponentFixture, TestBed, fakeAsync, tick } from "@angular/core/testing";
import { HorizontalWheelComponent } from "./horizontal-wheel.component";
import { CommonModule } from "@angular/common";
import { Component, ViewChild, ElementRef, signal } from "@angular/core";

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

  it("should emit onSelect when value changes by scroll", fakeAsync(() => {
    const itemElements = [
      {
        nativeElement: {
          getBoundingClientRect: () => ({ left: 0, width: 100 }),
          offsetWidth: 100,
          offsetLeft: 0,
          style: { transform: "", opacity: "" }
        }
      },
      {
        nativeElement: {
          getBoundingClientRect: () => ({ left: 100, width: 100 }),
          offsetWidth: 100,
          offsetLeft: 100,
          style: { transform: "", opacity: "" }
        }
      },
      {
        nativeElement: {
          getBoundingClientRect: () => ({ left: 200, width: 100 }),
          offsetWidth: 100,
          offsetLeft: 200,
          style: { transform: "", opacity: "" }
        }
      }
    ];

    const containerElement = {
      addEventListener: () => {},
      removeEventListener: () => {},
      getBoundingClientRect: () => ({ left: 0, width: 300 }),
      style: { setProperty: () => {} },
      scrollLeft: 50
    } as any;

    (component as any).containerElement = containerElement;
    (component as any).items = signal(itemElements);

    jest.spyOn(host, "onSelect");

    component.onScroll();
    tick();

    expect(host.onSelect).toHaveBeenCalledWith("B");
  }));

  it("should center element by index on item click", () => {
    const containerElement = document.createElement("div");
    (containerElement as any).scrollTo = () => {};
    (component as any).containerElement = containerElement;
    const scrollToSpy = jest.spyOn(containerElement, "scrollTo");

    const itemElements = [
      { nativeElement: { offsetLeft: 50, offsetWidth: 100 } },
      { nativeElement: { offsetLeft: 150, offsetWidth: 100 } },
      { nativeElement: { offsetLeft: 250, offsetWidth: 100 } }
    ];
    (component as any).items = signal(itemElements);
        Object.defineProperty((component as any).containerElement, 'offsetWidth', {
      get: () => 200,
    });

    const fakeEvent = { preventDefault: () => {} } as any as MouseEvent;
    component.onItemClick(fakeEvent, 1);

        expect(scrollToSpy).toHaveBeenCalledWith({ behavior: "smooth", left: 100 });
  });

  it("should handle mouse down and dragging", () => {
    const containerElement = document.createElement("div");
    containerElement.scrollLeft = 0;
    const fakeEvent = {
      currentTarget: containerElement,
      pageX: 100
    } as any as MouseEvent;

    component.onMouseDown(fakeEvent);

    expect(component.isDragging).toBe(true);
    expect(component.startX).toBe(100);
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

  it("should stop dragging and center closest item on mouse up", fakeAsync(() => {
    component.isDragging = true;
    (component as any).containerElement = {
      scrollLeft: 0,
      offsetWidth: 100,
      scrollTo: () => {}
    } as any;

    const itemElements = [
      { nativeElement: { offsetLeft: 0, offsetWidth: 50 } },
      { nativeElement: { offsetLeft: 50, offsetWidth: 50 } }
    ];
    (component as any).items = signal(itemElements);

    const centerElementByIndexSpy = jest.spyOn(component, "centerElementByIndex" as any);
    component.onMouseUp({} as MouseEvent);

    expect(component.isDragging).toBe(false);
    expect(centerElementByIndexSpy).toHaveBeenCalledWith(0);
  }));
});