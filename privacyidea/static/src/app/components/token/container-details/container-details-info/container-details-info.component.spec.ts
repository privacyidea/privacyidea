import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerDetailsInfoComponent } from './container-details-info.component';

describe('ContainerDetailsInfoComponent', () => {
  let component: ContainerDetailsInfoComponent;
  let fixture: ComponentFixture<ContainerDetailsInfoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsInfoComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsInfoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
