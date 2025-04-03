import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerCreateComponent } from './container-create.component';

describe('ContainerCreateComponent', () => {
  let component: ContainerCreateComponent;
  let fixture: ComponentFixture<ContainerCreateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerCreateComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainerCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
