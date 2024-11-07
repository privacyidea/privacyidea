import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerDetailsComponent } from './container-details.component';

describe('ContainerDetailsComponent', () => {
  let component: ContainerDetailsComponent;
  let fixture: ComponentFixture<ContainerDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
